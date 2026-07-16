import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import engine, Base
from routers import ingredients, recipes
from routers import auth as auth_router
from routers import purchases as purchases_router
from routers import stock as stock_router
from routers import channels as channels_router
from routers import categories as categories_router
import models  # noqa: F401 — registers all models before create_all

_NEW_INGREDIENT_COLS = [
    "ALTER TABLE ingredients ADD COLUMN purchase_unit VARCHAR(50)",
    "ALTER TABLE ingredients ADD COLUMN purchase_quantity FLOAT",
    "ALTER TABLE ingredients ADD COLUMN purchase_cost FLOAT",
    "ALTER TABLE ingredients ADD COLUMN yield_percentage FLOAT DEFAULT 100.0",
    "ALTER TABLE ingredients ADD COLUMN reduction_stages TEXT",
    "ALTER TABLE ingredients ADD COLUMN processing_cost_per_unit FLOAT",
    "ALTER TABLE ingredients ADD COLUMN processing_cost_per_batch FLOAT",
    "ALTER TABLE ingredients ADD COLUMN processing_batch_size FLOAT",
]

_NEW_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS sales_channels (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(120) NOT NULL,
        fee_percent FLOAT,
        fixed_cost FLOAT,
        CONSTRAINT uq_channel_user_name UNIQUE (user_id, name)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_sales_channels_user_id ON sales_channels (user_id)",
    """
    CREATE TABLE IF NOT EXISTS recipe_channel_prices (
        id SERIAL PRIMARY KEY,
        recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
        channel_id INTEGER NOT NULL REFERENCES sales_channels(id) ON DELETE CASCADE,
        sale_price FLOAT NOT NULL,
        CONSTRAINT uq_recipe_channel UNIQUE (recipe_id, channel_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_recipe_channel_prices_recipe_id ON recipe_channel_prices (recipe_id)",
    "CREATE INDEX IF NOT EXISTS ix_recipe_channel_prices_channel_id ON recipe_channel_prices (channel_id)",
    """
    CREATE TABLE IF NOT EXISTS recipe_channel_ingredients (
        id SERIAL PRIMARY KEY,
        recipe_channel_price_id INTEGER NOT NULL REFERENCES recipe_channel_prices(id) ON DELETE CASCADE,
        ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
        quantity FLOAT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS categories (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(100) NOT NULL,
        CONSTRAINT uq_category_user_name UNIQUE (user_id, name)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_categories_user_id ON categories (user_id)",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Each statement below runs in its own transaction: in Postgres, one
    # failed statement (e.g. "column already exists") aborts the whole
    # transaction, silently skipping every statement that follows it if
    # they all shared a single connection/transaction.
    for stmt in _NEW_INGREDIENT_COLS:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt))
        except Exception:
            pass  # column already exists

    for stmt in _NEW_TABLES:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt))
        except Exception:
            pass  # table/index already exists

    # Normalize reduction_stages: re-encode rows stored as raw TEXT string
    # before the column was treated as JSON at the ORM level.
    try:
        async with engine.begin() as conn:
            rows = (await conn.execute(
                text("SELECT id, reduction_stages FROM ingredients WHERE reduction_stages IS NOT NULL")
            )).fetchall()
        for row_id, val in rows:
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    async with engine.begin() as conn:
                        await conn.execute(
                            text("UPDATE ingredients SET reduction_stages = :v WHERE id = :id"),
                            {"v": json.dumps(parsed), "id": row_id},
                        )
                except Exception:
                    pass
    except Exception:
        pass
    yield


app = FastAPI(title="Gestão de Restaurante", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(ingredients.router, prefix="/api/ingredientes", tags=["Ingredientes"])
app.include_router(recipes.router, prefix="/api/receitas", tags=["Receitas"])
app.include_router(purchases_router.router, prefix="/api/compras", tags=["Compras"])
app.include_router(stock_router.router, prefix="/api/estoque", tags=["Estoque"])
app.include_router(channels_router.router, prefix="/api/canais", tags=["Canais de Venda"])
app.include_router(categories_router.router, prefix="/api/categorias", tags=["Categorias"])


@app.get("/")
def root():
    return {"message": "API - Sistema de Gestão de Restaurante v2.0"}
