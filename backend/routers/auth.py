from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
import models
import schemas
from auth import hash_password, verify_password, create_access_token

router = APIRouter()


@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
async def register(data: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(400, "E-mail já cadastrado")
    if len(data.password) < 6:
        raise HTTPException(400, "Senha deve ter pelo menos 6 caracteres")
    user = models.User(email=data.email, hashed_password=hash_password(data.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"access_token": create_access_token({"sub": str(user.id)}), "token_type": "bearer"}


@router.post("/login", response_model=schemas.TokenResponse)
async def login(data: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "E-mail ou senha incorretos")
    return {"access_token": create_access_token({"sub": str(user.id)}), "token_type": "bearer"}
