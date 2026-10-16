from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import get_current_user, hash_password
import models
import schemas

router = APIRouter()

MIN_PASSWORD = 6


def _check_role(role: str) -> None:
    if role not in models.ROLES:
        raise HTTPException(400, "Perfil inválido. Use 'master' ou 'operacao'.")


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise HTTPException(400, f"Senha deve ter pelo menos {MIN_PASSWORD} caracteres")


async def _get_account_user(db: AsyncSession, current: models.User, user_id: int) -> models.User:
    # Só enxerga usuários da própria conta; qualquer outro id é "não encontrado".
    result = await db.execute(
        select(models.User).where(
            models.User.id == user_id,
            models.User.account_id == current.account_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    return user


@router.get("/", response_model=List[schemas.UserAdminResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.User)
        .where(models.User.account_id == current_user.account_id)
        .order_by(models.User.role, models.User.email)
    )
    return result.scalars().all()


@router.post("/", response_model=schemas.UserAdminResponse, status_code=201)
async def create_user(
    data: schemas.UserAdminCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _check_role(data.role)
    _check_password(data.password)
    dup = await db.execute(select(models.User).where(models.User.email == data.email))
    if dup.scalar_one_or_none():
        raise HTTPException(400, "E-mail já cadastrado")
    user = models.User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
        is_active=True,
        account_id=current_user.account_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/{user_id}", response_model=schemas.UserAdminResponse)
async def update_user(
    user_id: int,
    data: schemas.UserAdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    target = await _get_account_user(db, current_user, user_id)
    is_self = target.id == current_user.id

    if data.role is not None:
        _check_role(data.role)
        if is_self and data.role != models.ROLE_MASTER:
            raise HTTPException(400, "Você não pode remover o seu próprio acesso Master")
        target.role = data.role
    if data.is_active is not None:
        if is_self and not data.is_active:
            raise HTTPException(400, "Você não pode desativar o seu próprio usuário")
        target.is_active = data.is_active
    if data.password is not None:
        _check_password(data.password)
        target.hashed_password = hash_password(data.password)

    await db.commit()
    await db.refresh(target)
    return target
