"""Perfis de acesso no nível do banco (PostgreSQL / Supabase).

Camadas aplicadas aqui, todas idempotentes e executadas na inicialização:

1. users.role / account_id / is_active (+ CHECK no domínio de role). Usuários que
   já existiam viram Master da própria conta, preservando todo o acesso atual.
2. Row Level Security habilitado em todas as tabelas do app. O backend conecta
   como dono das tabelas (ignora RLS); a API de dados do Supabase (anon /
   authenticated) deixa de enxergar qualquer linha.
3. Papel `operacao_ro`: sem login, com SELECT apenas nas colunas NÃO financeiras
   de ingredientes e receitas. As requisições do perfil Operação rodam sob esse
   papel (SET LOCAL ROLE), então o próprio Postgres recusa ler custo, preço,
   compras, estoque, fornecedores etc., mesmo que o código tenha um erro.
   Uma política RLS ainda limita as linhas à conta do usuário.
"""
import logging

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from database import Base

logger = logging.getLogger("restaurante.rbac")

OPERACAO_DB_ROLE = "operacao_ro"
ACCOUNT_SETTING = "app.account_id"

# Única superfície de leitura do perfil Operação. Nada financeiro entra aqui.
OPERACAO_COLUMN_GRANTS: dict[str, tuple[str, ...]] = {
    "ingredients": ("id", "user_id", "name", "unit", "yield_percentage", "reduction_stages"),
    "recipes": (
        "id", "user_id", "name", "description", "category", "yield_portions",
        "stock_unit", "is_proportional", "proportion_base_ingredient_id",
    ),
    "recipe_ingredients": ("id", "recipe_id", "ingredient_id", "quantity"),
    "recipe_sub_recipes": ("id", "parent_recipe_id", "sub_recipe_id", "portions"),
}

_OWNER_PREDICATES = {
    "ingredients": "user_id = NULLIF(current_setting('app.account_id', true), '')::int",
    "recipes": "user_id = NULLIF(current_setting('app.account_id', true), '')::int",
    "recipe_ingredients": (
        "EXISTS (SELECT 1 FROM recipes r WHERE r.id = recipe_id "
        "AND r.user_id = NULLIF(current_setting('app.account_id', true), '')::int)"
    ),
    "recipe_sub_recipes": (
        "EXISTS (SELECT 1 FROM recipes r WHERE r.id = parent_recipe_id "
        "AND r.user_id = NULLIF(current_setting('app.account_id', true), '')::int)"
    ),
}

# (consulta, deve funcionar?) — verificada sob o papel restrito a cada inicialização.
_SELF_TEST = [
    ("SELECT id, name, unit, yield_percentage FROM ingredients LIMIT 1", True),
    ("SELECT id, name, category, yield_portions, description FROM recipes LIMIT 1", True),
    ("SELECT quantity FROM recipe_ingredients LIMIT 1", True),
    ("SELECT unit_cost FROM ingredients LIMIT 1", False),
    ("SELECT purchase_cost FROM ingredients LIMIT 1", False),
    ("SELECT processing_cost_per_unit FROM ingredients LIMIT 1", False),
    ("SELECT sale_price FROM recipes LIMIT 1", False),
    ("SELECT * FROM recipes LIMIT 1", False),
    ("SELECT * FROM ingredients LIMIT 1", False),
    ("SELECT 1 FROM users LIMIT 1", False),
    ("SELECT 1 FROM purchases LIMIT 1", False),
    ("SELECT 1 FROM purchase_items LIMIT 1", False),
    ("SELECT 1 FROM suppliers LIMIT 1", False),
    ("SELECT 1 FROM sales_channels LIMIT 1", False),
    ("SELECT 1 FROM recipe_channel_prices LIMIT 1", False),
    ("SELECT 1 FROM stock LIMIT 1", False),
]

_state = {"operacao_ready": False}


def operacao_role_ready() -> bool:
    return _state["operacao_ready"]


async def _exec(engine: AsyncEngine, sql: str, label: str) -> bool:
    try:
        async with engine.begin() as conn:
            await conn.execute(text(sql))
        return True
    except Exception as exc:  # noqa: BLE001 — cada passo é isolado de propósito
        logger.error("RBAC: passo '%s' falhou: %s", label, exc)
        return False


async def _migrate_users(engine: AsyncEngine) -> None:
    steps = [
        ("users.role", "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'master'"),
        ("users.account_id", "ALTER TABLE users ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES users(id)"),
        ("users.is_active", "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE"),
        ("ix_users_account_id", "CREATE INDEX IF NOT EXISTS ix_users_account_id ON users (account_id)"),
        ("backfill account_id", "UPDATE users SET account_id = id WHERE account_id IS NULL"),
        (
            "ck_users_role",
            """
            DO $$ BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_users_role') THEN
                ALTER TABLE users ADD CONSTRAINT ck_users_role CHECK (role IN ('master', 'operacao'));
              END IF;
            END $$
            """,
        ),
    ]
    for label, sql in steps:
        await _exec(engine, sql, label)


async def _enable_rls(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        bypass = bool(
            (await conn.execute(
                text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user")
            )).scalar()
        )
        owned = {
            row[0]
            for row in (await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tableowner = current_user")
            )).all()
        }
    for table in Base.metadata.sorted_tables:
        name = table.name
        if bypass or name in owned:
            await _exec(engine, f'ALTER TABLE "{name}" ENABLE ROW LEVEL SECURITY', f"rls:{name}")
        else:
            logger.warning(
                "RBAC: RLS não habilitado em %s (a conexão não é dona da tabela nem ignora RLS)", name
            )


async def _setup_operacao_role(engine: AsyncEngine) -> None:
    role = OPERACAO_DB_ROLE
    await _exec(
        engine,
        f"""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
            CREATE ROLE {role} NOLOGIN NOINHERIT NOBYPASSRLS;
          END IF;
        END $$
        """,
        "create role",
    )
    await _exec(engine, f"GRANT {role} TO CURRENT_USER", "grant membership")
    await _exec(engine, f"GRANT USAGE ON SCHEMA public TO {role}", "grant usage")
    # Recomeça do zero a cada inicialização: se uma coluna deixar de constar na
    # lista acima, a permissão antiga não sobrevive.
    await _exec(engine, f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role}", "revoke all")
    for table, columns in OPERACAO_COLUMN_GRANTS.items():
        cols = ", ".join(columns)
        await _exec(engine, f"GRANT SELECT ({cols}) ON {table} TO {role}", f"grant:{table}")
        predicate = _OWNER_PREDICATES[table]
        await _exec(
            engine,
            f"""
            DO $$ BEGIN
              DROP POLICY IF EXISTS operacao_ro_select ON {table};
              CREATE POLICY operacao_ro_select ON {table} FOR SELECT TO {role} USING ({predicate});
            END $$
            """,
            f"policy:{table}",
        )


async def verify_operacao_role(engine: AsyncEngine) -> bool:
    ok = True
    for query, should_work in _SELF_TEST:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(f"SET LOCAL ROLE {OPERACAO_DB_ROLE}"))
                await conn.execute(text(query))
            worked = True
        except Exception:  # noqa: BLE001
            worked = False
        if worked != should_work:
            ok = False
            logger.error(
                "RBAC: autoteste falhou — '%s' %s sob %s",
                query, "foi bloqueada" if should_work else "FOI PERMITIDA", OPERACAO_DB_ROLE,
            )
    return ok


async def apply_rbac_migrations(engine: AsyncEngine) -> None:
    _state["operacao_ready"] = False
    if engine.dialect.name != "postgresql":
        logger.error("RBAC: dialeto %s sem suporte; perfil Operação ficará indisponível", engine.dialect.name)
        return
    await _migrate_users(engine)
    await _enable_rls(engine)
    await _setup_operacao_role(engine)
    _state["operacao_ready"] = await verify_operacao_role(engine)
    if _state["operacao_ready"]:
        logger.info("RBAC: papel %s verificado — perfil Operação habilitado", OPERACAO_DB_ROLE)
    else:
        logger.error("RBAC: papel %s NÃO verificado — perfil Operação bloqueado (fail-closed)", OPERACAO_DB_ROLE)


async def enter_operacao_role(db: AsyncSession, account_id: int) -> None:
    """Faz o restante da transação rodar sob o papel restrito.

    Deve ser chamado antes de qualquer consulta de dados do perfil Operação e
    essas rotas não podem fazer commit/rollback (isso encerraria a transação e
    devolveria o papel original).
    """
    if not _state["operacao_ready"]:
        raise HTTPException(503, "Perfil Operação indisponível: restrição do banco não verificada")
    await db.execute(text(f"SET LOCAL ROLE {OPERACAO_DB_ROLE}"))
    await db.execute(
        text("SELECT set_config(:key, :val, true)"),
        {"key": ACCOUNT_SETTING, "val": str(int(account_id))},
    )
