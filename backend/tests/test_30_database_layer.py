"""A restrição também vale no banco, independentemente do código da aplicação."""
import asyncpg
import pytest
from sqlalchemy import select

from conftest import asyncpg_dsn

APP_TABLES_QUERY = (
    "SELECT c.relname AS name, c.relrowsecurity AS rls FROM pg_class c "
    "JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relkind = 'r' ORDER BY 1"
)


@pytest.fixture
async def conn(world):
    c = await asyncpg.connect(asyncpg_dsn())
    yield c
    await c.close()


async def as_role(conn, role, sql, account=None):
    """Executa uma consulta numa transação própria sob um papel do banco."""
    async with conn.transaction():
        await conn.execute(f"SET LOCAL ROLE {role}")
        if account is not None:
            await conn.execute("SELECT set_config('app.account_id', $1, true)", str(account))
        return await conn.fetch(sql)


# ── Row Level Security: a API de dados do Supabase não enxerga nada ──────────

async def test_rls_is_enabled_on_every_table(conn):
    rows = await conn.fetch(APP_TABLES_QUERY)
    assert len(rows) >= 15
    assert [r["name"] for r in rows if not r["rls"]] == []


@pytest.mark.parametrize("role", ["anon", "authenticated"])
async def test_supabase_data_api_roles_see_no_rows(conn, role):
    assert await conn.fetchval("SELECT has_table_privilege($1, 'ingredients', 'SELECT')", role) is True
    assert await conn.fetchval("SELECT count(*) FROM ingredients") > 0
    for row in await conn.fetch(APP_TABLES_QUERY):
        got = await as_role(conn, role, f'SELECT count(*) AS n FROM "{row["name"]}"')
        assert got[0]["n"] == 0, f"{role} leu linhas de {row['name']}"


# ── Papel restrito da Operação ───────────────────────────────────────────────

async def test_operacao_role_is_locked_down(conn):
    r = await conn.fetchrow(
        "SELECT rolcanlogin, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = 'operacao_ro'"
    )
    assert not any(r.values())


async def test_operacao_role_reads_only_non_financial_columns_of_its_restaurant(conn):
    got = await as_role(conn, "operacao_ro", "SELECT id, name, unit, yield_percentage, reduction_stages FROM ingredients", account=1)
    names = {r["name"] for r in got}
    assert {"Salmão", "Cream Cheese", "Sal"} <= names and "Camarão" not in names

    got = await as_role(conn, "operacao_ro", "SELECT id, name, unit FROM ingredients", account=2)
    assert {r["name"] for r in got} == {"Camarão"}

    # sem a conta definida a política RLS não libera nenhuma linha
    assert await as_role(conn, "operacao_ro", "SELECT id, name FROM ingredients") == []

    got = await as_role(conn, "operacao_ro", "SELECT id, name, category, yield_portions, description FROM recipes", account=1)
    assert {r["name"] for r in got} >= {"Recheio de Salmão", "Molho"} and "Bobó" not in {r["name"] for r in got}
    got = await as_role(conn, "operacao_ro", "SELECT recipe_id, ingredient_id, quantity FROM recipe_ingredients", account=1)
    assert len(got) >= 4 and {r["recipe_id"] for r in got} <= {1, 2}


DENIED_READS = [
    "SELECT unit_cost FROM ingredients",
    "SELECT purchase_cost FROM ingredients",
    "SELECT purchase_quantity FROM ingredients",
    "SELECT processing_cost_per_unit FROM ingredients",
    "SELECT processing_cost_per_batch FROM ingredients",
    "SELECT min_stock FROM ingredients",
    "SELECT sale_price FROM recipes",
    "SELECT min_stock FROM recipes",
    "SELECT * FROM ingredients",
    "SELECT * FROM recipes",
    "SELECT i FROM ingredients i",
    "SELECT to_jsonb(r) FROM recipes r",
    "SELECT sum(unit_cost) FROM ingredients",
    "SELECT id FROM ingredients WHERE unit_cost > 5",
    "SELECT id FROM recipes ORDER BY sale_price",
    "SELECT * FROM users",
    "SELECT hashed_password FROM users",
    "SELECT * FROM purchases",
    "SELECT * FROM purchase_items",
    "SELECT * FROM suppliers",
    "SELECT * FROM sales_channels",
    "SELECT * FROM recipe_channel_prices",
    "SELECT * FROM recipe_channel_ingredients",
    "SELECT * FROM stock",
    "SELECT * FROM stock_movements",
    "SELECT * FROM recipe_stock",
    "SELECT * FROM recipe_stock_movements",
    "SELECT * FROM categories",
]


@pytest.mark.parametrize("sql", DENIED_READS)
async def test_operacao_role_is_denied_financial_reads(conn, sql):
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await as_role(conn, "operacao_ro", sql, account=1)


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO ingredients (user_id, name, unit, unit_cost) VALUES (1, 'x', 'kg', 1)",
        "UPDATE ingredients SET name = 'hack'",
        "DELETE FROM ingredients",
        "UPDATE recipes SET name = 'hack'",
        "DELETE FROM recipes",
        "UPDATE recipe_ingredients SET quantity = 0",
        "UPDATE users SET role = 'master'",
    ],
)
async def test_operacao_role_cannot_write(conn, sql):
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE operacao_ro")
            await conn.execute(sql)


async def test_role_column_only_accepts_known_profiles(conn):
    with pytest.raises(asyncpg.CheckViolationError):
        await conn.execute("INSERT INTO users (email, hashed_password, role) VALUES ('x@y.com', 'h', 'admin')")


# ── Mesmo um erro no código seria barrado pelo banco ─────────────────────────

async def test_orm_query_for_all_columns_is_blocked_under_operacao(world):
    import database
    import models
    import rbac_db

    async with database.AsyncSessionLocal() as db:
        await rbac_db.enter_operacao_role(db, 1)
        with pytest.raises(Exception) as exc:
            await db.execute(select(models.Ingredient))  # traria unit_cost etc.
        assert "permission denied" in str(exc.value).lower()

    async with database.AsyncSessionLocal() as db:
        await rbac_db.enter_operacao_role(db, 1)
        with pytest.raises(Exception) as exc:
            await db.execute(select(models.Purchase))
        assert "permission denied" in str(exc.value).lower()

    # a conexão volta ao papel normal depois da transação
    async with database.AsyncSessionLocal() as db:
        assert (await db.execute(select(models.Ingredient.unit_cost).limit(1))).first() is not None


async def test_operacao_fails_closed_when_database_role_is_unverified(world):
    import rbac_db

    assert rbac_db.operacao_role_ready()
    rbac_db._state["operacao_ready"] = False
    try:
        blocked = await world.client.get("/api/ingredientes/", headers=world.auth("operacao"))
        assert blocked.status_code == 503
        assert "unit_cost" not in blocked.text
        assert (await world.client.get("/api/ingredientes/", headers=world.auth("owner"))).status_code == 200
    finally:
        rbac_db._state["operacao_ready"] = True


async def test_startup_migration_is_idempotent(world):
    import database
    import rbac_db

    await rbac_db.apply_rbac_migrations(database.engine)
    await rbac_db.apply_rbac_migrations(database.engine)
    assert rbac_db.operacao_role_ready()
    got = await world.client.get("/api/receitas/", headers=world.auth("operacao"))
    assert got.status_code == 200
