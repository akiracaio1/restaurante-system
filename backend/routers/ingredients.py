from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database import get_db
from auth import get_current_user
import models
import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.IngredientResponse])
async def list_ingredients(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Ingredient)
        .where(models.Ingredient.user_id == current_user.id)
        .order_by(models.Ingredient.name)
    )
    return result.scalars().all()


@router.post("/", response_model=schemas.IngredientResponse, status_code=201)
async def create_ingredient(
    data: schemas.IngredientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    dup = await db.execute(
        select(models.Ingredient).where(
            models.Ingredient.user_id == current_user.id,
            models.Ingredient.name == data.name,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(400, "Ingrediente com este nome já existe")
    obj = models.Ingredient(**data.model_dump(), user_id=current_user.id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{ingredient_id}", response_model=schemas.IngredientResponse)
async def get_ingredient(
    ingredient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Ingredient).where(
            models.Ingredient.id == ingredient_id,
            models.Ingredient.user_id == current_user.id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Ingrediente não encontrado")
    return obj


@router.put("/{ingredient_id}", response_model=schemas.IngredientResponse)
async def update_ingredient(
    ingredient_id: int,
    data: schemas.IngredientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Ingredient).where(
            models.Ingredient.id == ingredient_id,
            models.Ingredient.user_id == current_user.id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Ingrediente não encontrado")
    dup = await db.execute(
        select(models.Ingredient).where(
            models.Ingredient.user_id == current_user.id,
            models.Ingredient.name == data.name,
            models.Ingredient.id != ingredient_id,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(400, "Ingrediente com este nome já existe")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{ingredient_id}", status_code=204)
async def delete_ingredient(
    ingredient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Ingredient).where(
            models.Ingredient.id == ingredient_id,
            models.Ingredient.user_id == current_user.id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Ingrediente não encontrado")
    in_use = await db.execute(
        select(models.RecipeIngredient).where(
            models.RecipeIngredient.ingredient_id == ingredient_id
        )
    )
    if in_use.scalar_one_or_none():
        raise HTTPException(400, "Ingrediente está sendo usado em uma ou mais receitas")
    await db.delete(obj)
    await db.commit()
