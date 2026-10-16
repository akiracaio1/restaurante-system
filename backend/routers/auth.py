from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
import models
import schemas
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_authenticated_user,
)

router = APIRouter()


@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
async def register(data: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    # Cadastro público só existe para criar o primeiro usuário (Master) de um
    # banco vazio. Depois disso, quem concede acesso é um Master em /api/usuarios.
    total = (await db.execute(select(func.count()).select_from(models.User))).scalar_one()
    if total > 0:
        raise HTTPException(
            403, "Cadastro público desativado. Peça a um usuário Master para criar o seu acesso."
        )
    if len(data.password) < 6:
        raise HTTPException(400, "Senha deve ter pelo menos 6 caracteres")
    user = models.User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role=models.ROLE_MASTER,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    user.account_id = user.id
    await db.commit()
    await db.refresh(user)
    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "token_type": "bearer",
        "role": user.role,
    }


@router.post("/login", response_model=schemas.TokenResponse)
async def login(data: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "E-mail ou senha incorretos")
    if not user.is_active:
        raise HTTPException(403, "Usuário desativado. Fale com um administrador (Master).")
    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "token_type": "bearer",
        "role": user.role,
    }


@router.get("/me", response_model=schemas.MeResponse)
async def me(user: models.User = Depends(get_authenticated_user)):
    return schemas.MeResponse(id=user.id, email=user.email, role=user.role)
