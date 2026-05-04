import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import engine, Base
from routers import ingredients, recipes
from routers import auth as auth_router
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in _NEW_INGREDIENT_COLS:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # column already exists
        # Normalize reduction_stages: re-encode rows stored as raw TEXT string
        # before the column was treated as JSON at the ORM level.
        try:
            rows = (await conn.execute(
                text("SELECT id, reduction_stages FROM ingredients WHERE reduction_stages IS NOT NULL")
            )).fetchall()
            for row_id, val in rows:
                if isinstance(val, str):
                    try:
                        parsed = json.loads(val)
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


@app.get("/")
def root():
    return {"message": "API - Sistema de Gestão de Restaurante v2.0"}
