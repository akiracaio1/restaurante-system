from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routers import ingredients, recipes
import models  # noqa: F401 — ensures models are registered before create_all

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Gestão de Restaurante", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingredients.router, prefix="/api/ingredientes", tags=["Ingredientes"])
app.include_router(recipes.router, prefix="/api/receitas", tags=["Receitas"])


@app.get("/")
def root():
    return {"message": "API - Sistema de Gestão de Restaurante v1.0"}
