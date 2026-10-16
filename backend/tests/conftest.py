"""Testes dos perfis de acesso (Master / Operação) contra um PostgreSQL de verdade.

Como rodar (a partir de backend/):

    # um Postgres descartável; o usuário precisa poder criar papéis e o nome do
    # banco precisa conter "test" (o teste APAGA todas as tabelas dele)
    set TEST_DATABASE_URL=postgresql+asyncpg://usuario:senha@127.0.0.1:5432/restaurante_test
    pytest

Sem TEST_DATABASE_URL todos os testes são ignorados. Nunca aponte para o banco
de produção.
"""
import os
import re

import asyncpg
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
TEST_SECRET = "test-secret-key-not-for-production"

if TEST_DATABASE_URL:
    _dbname = TEST_DATABASE_URL.rsplit("/", 1)[-1].split("?")[0]
    if "test" not in _dbname.lower():
        pytest.exit(
            f"TEST_DATABASE_URL aponta para '{_dbname}'. Por segurança só rodo em bancos com 'test' no nome.",
            returncode=2,
        )
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["JWT_SECRET_KEY"] = TEST_SECRET


def pytest_collection_modifyitems(config, items):
    if not TEST_DATABASE_URL:
        skip = pytest.mark.skip(reason="defina TEST_DATABASE_URL (postgresql+asyncpg://...)")
        for item in items:
            item.add_marker(skip)


def asyncpg_dsn() -> str:
    return TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


async def reset_database() -> None:
    """Apaga todas as tabelas e prepara papéis iguais aos do Supabase (anon/authenticated)."""
    conn = await asyncpg.connect(asyncpg_dsn())
    try:
        for row in await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"):
            await conn.execute(f'DROP TABLE IF EXISTS "{row["tablename"]}" CASCADE')
        for role in ("anon", "authenticated"):
            if not await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", role):
                await conn.execute(f"CREATE ROLE {role} NOLOGIN")
            try:
                await conn.execute(f"GRANT {role} TO CURRENT_USER")
            except asyncpg.PostgresError:
                pass
        await conn.execute("GRANT USAGE ON SCHEMA public TO anon, authenticated")
        # Como no Supabase: tabelas novas do schema public ficam expostas à API de dados
        await conn.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated")
    finally:
        await conn.close()


# ── Banco no formato ANTIGO (antes dos perfis) com dados de dois restaurantes ──

CANARIES = {
    # valores financeiros inconfundíveis: não podem aparecer em nenhuma resposta da Operação
    "unit_cost_salmao": "7.7123",
    "unit_cost_cream": "33.3333",
    "purchase_cost": "123.4567",
    "processing": "1.2345",
    "sale_price": "49.9123",
    "channel_price": "59.9876",
    "fee_percent": "12.3456",
    "fixed_cost": "0.9876",
    "purchase_total": "321.1234",
    "supplier_cnpj": "12.345.678/0001-90",
    "other_account_cost": "55.5555",
}

LEGACY_SQL = [
    # restaurante A (usuário 1) e restaurante B (usuário 2): contas independentes, como em produção hoje
    "INSERT INTO ingredients (id, user_id, name, unit, unit_cost, min_stock, purchase_unit, purchase_quantity, purchase_cost, yield_percentage, processing_cost_per_unit) "
    "VALUES (1, 1, 'Salmão', 'kg', 7.7123, 1, 'caixa', 5, 123.4567, 80, 1.2345),"
    "       (2, 1, 'Cream Cheese', 'kg', 33.3333, 0, NULL, NULL, NULL, 100, NULL),"
    "       (3, 1, 'Sal', 'kg', 2.5, 0, NULL, NULL, NULL, 100, NULL),"
    "       (4, 2, 'Camarão', 'kg', 55.5555, 0, NULL, NULL, NULL, 100, NULL)",
    "INSERT INTO recipes (id, user_id, name, description, category, sale_price, yield_portions, stock_unit, is_proportional, proportion_base_ingredient_id) "
    "VALUES (1, 1, 'Recheio de Salmão', 'Grelhe o salmão e misture com o cream cheese.', 'prato principal', 49.9123, 10, 'porção', true, 1),"
    "       (2, 1, 'Molho', 'Molho simples', 'entrada', 5.5, 4, 'porção', false, NULL),"
    "       (3, 2, 'Bobó', 'Receita da outra conta', 'prato principal', 40, 2, 'porção', false, NULL)",
    "INSERT INTO recipe_ingredients (id, recipe_id, ingredient_id, quantity) "
    "VALUES (1, 1, 1, 1.0), (2, 1, 2, 0.4), (3, 1, 3, 0.01), (4, 2, 3, 0.2), (5, 3, 4, 1.0)",
    "INSERT INTO recipe_sub_recipes (id, parent_recipe_id, sub_recipe_id, portions) VALUES (1, 1, 2, 2)",
    "INSERT INTO sales_channels (id, user_id, name, fee_percent, fixed_cost) VALUES (1, 1, 'iFood', 12.3456, 0.9876)",
    "INSERT INTO recipe_channel_prices (id, recipe_id, channel_id, sale_price) VALUES (1, 1, 1, 59.9876)",
    "INSERT INTO suppliers (id, user_id, name, cnpj) VALUES (1, 1, 'Peixaria X', '12.345.678/0001-90')",
    "INSERT INTO purchases (id, user_id, date, supplier, supplier_id, tax, freight, created_at) "
    "VALUES (1, 1, '2026-09-01', 'Peixaria X', 1, 1.11, 2.22, '2026-09-01 10:00:00')",
    "INSERT INTO purchase_items (id, purchase_id, ingredient_id, quantity, unit, total_price, allocated_extra, unit_cost, previous_unit_cost) "
    "VALUES (1, 1, 1, 5, 'kg', 321.1234, 0, 64.22, 7.0)",
    "INSERT INTO stock (id, user_id, ingredient_id, quantity) VALUES (1, 1, 1, 3)",
]

SEQUENCE_TABLES = [
    "users", "ingredients", "recipes", "recipe_ingredients", "recipe_sub_recipes", "sales_channels",
    "recipe_channel_prices", "suppliers", "purchases", "purchase_items", "stock",
]

OWNER_EMAIL, OWNER_PASSWORD = "owner@restaurante-a.com", "owner-pass-1"
OTHER_EMAIL, OTHER_PASSWORD = "dono@restaurante-b.com", "other-pass-1"


async def build_legacy_database() -> None:
    import auth
    import database

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)
        # volta a tabela users ao formato de antes dos perfis
        await conn.execute(text("ALTER TABLE users DROP CONSTRAINT ck_users_role"))
        await conn.execute(text("ALTER TABLE users DROP COLUMN account_id, DROP COLUMN role, DROP COLUMN is_active"))
        for uid, email, pwd in ((1, OWNER_EMAIL, OWNER_PASSWORD), (2, OTHER_EMAIL, OTHER_PASSWORD)):
            await conn.execute(
                text("INSERT INTO users (id, email, hashed_password) VALUES (:i, :e, :h)"),
                {"i": uid, "e": email, "h": auth.hash_password(pwd)},
            )
        for stmt in LEGACY_SQL:
            await conn.execute(text(stmt))
        for table in SEQUENCE_TABLES:
            await conn.execute(
                text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), (SELECT max(id) FROM {table}))")
            )


class World:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.tokens: dict[str, str] = {}
        self.ids: dict[str, int] = {}

    def auth(self, who: str) -> dict:
        return {"Authorization": f"Bearer {self.tokens[who]}"}

    async def login(self, email: str, password: str) -> str:
        r = await self.client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return r.json()["access_token"]

    async def setup(self) -> None:
        self.tokens["owner"] = await self.login(OWNER_EMAIL, OWNER_PASSWORD)
        self.tokens["other"] = await self.login(OTHER_EMAIL, OTHER_PASSWORD)
        for key, email, role in (
            ("operacao", "funcionaria@restaurante-a.com", "operacao"),
            ("partner", "socio@restaurante-a.com", "master"),
        ):
            r = await self.client.post(
                "/api/usuarios/",
                headers=self.auth("owner"),
                json={"email": email, "password": f"{key}-pass-1", "role": role},
            )
            assert r.status_code == 201, r.text
            self.ids[key] = r.json()["id"]
            self.tokens[key] = await self.login(email, f"{key}-pass-1")
        self.ids["owner"] = (await self.client.get("/api/auth/me", headers=self.auth("owner"))).json()["id"]
        self.ids["other"] = (await self.client.get("/api/auth/me", headers=self.auth("other"))).json()["id"]


@pytest_asyncio.fixture(scope="session")
async def world():
    await reset_database()
    await build_legacy_database()
    import main

    async with main.app.router.lifespan_context(main.app):
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            w = World(client)
            await w.setup()
            yield w
    await main.engine.dispose()


# chaves de JSON que nunca podem existir em respostas do perfil Operação
FINANCIAL_KEY = re.compile(
    r"cost|price|preco|custo|cmv|margin|margem|profit|lucro|fee|purchase|processing|subtotal|total|spent|cnpj|supplier|channel",
    re.IGNORECASE,
)


def all_keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from all_keys(v)
    elif isinstance(node, list):
        for item in node:
            yield from all_keys(item)
