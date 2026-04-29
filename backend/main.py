from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routers import ingredients, recipes
from routers import auth as auth_router
import models  # noqa: F401 — registers all models before create_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
