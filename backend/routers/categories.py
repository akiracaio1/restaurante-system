from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database import get_db
from auth import get_current_user
import models
import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Category)
        .where(models.Category.user_id == current_user.id)
        .order_by(models.Category.name)
    )
    return result.scalars().all()


@router.post("/", response_model=schemas.CategoryResponse, status_code=201)
async def create_category(
    data: schemas.CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    dup = await db.execute(
        select(models.Category).where(
            models.Category.user_id == current_user.id,
            models.Category.name == data.name,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(400, "Categoria com este nome já existe")
    obj = models.Category(name=data.name, user_id=current_user.id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.put("/{category_id}", response_model=schemas.CategoryResponse)
async def update_category(
    category_id: int,
    data: schemas.CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Category).where(
            models.Category.id == category_id,
            models.Category.user_id == current_user.id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Categoria não encontrada")

    dup = await db.execute(
        select(models.Category).where(
            models.Category.user_id == current_user.id,
            models.Category.name == data.name,
            models.Category.id != category_id,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(400, "Categoria com este nome já existe")

    old_name = obj.name
    obj.name = data.name
    if old_name != data.name:
        await db.execute(
            update(models.Recipe)
            .where(
                models.Recipe.user_id == current_user.id,
                models.Recipe.category == old_name,
            )
            .values(category=data.name)
        )
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Category).where(
            models.Category.id == category_id,
            models.Category.user_id == current_user.id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Categoria não encontrada")
    await db.delete(obj)
    await db.commit()
