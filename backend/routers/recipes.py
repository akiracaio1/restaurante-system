from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List

from database import get_db
from auth import get_current_user
import models
import schemas

router = APIRouter()


def build_response(recipe: models.Recipe) -> schemas.RecipeResponse:
    total_cost = 0.0
    ingredients_resp = []
    for ri in recipe.recipe_ingredients:
        real_cost = ri.ingredient.real_unit_cost
        subtotal = real_cost * ri.quantity
        total_cost += subtotal
        ingredients_resp.append(
            schemas.RecipeIngredientResponse(
                id=ri.id,
                ingredient_id=ri.ingredient_id,
                ingredient_name=ri.ingredient.name,
                ingredient_unit=ri.ingredient.unit,
                ingredient_unit_cost=real_cost,
                quantity=ri.quantity,
                subtotal=round(subtotal, 4),
            )
        )
    cmv = (total_cost / recipe.sale_price * 100) if recipe.sale_price > 0 else 0.0
    return schemas.RecipeResponse(
        id=recipe.id,
        name=recipe.name,
        description=recipe.description,
        category=recipe.category,
        sale_price=recipe.sale_price,
        yield_portions=recipe.yield_portions,
        ingredients=ingredients_resp,
        total_cost=round(total_cost, 4),
        cmv_percent=round(cmv, 2),
    )


def _with_ingredients():
    return selectinload(models.Recipe.recipe_ingredients).selectinload(
        models.RecipeIngredient.ingredient
    )


@router.get("/", response_model=List[schemas.RecipeResponse])
async def list_recipes(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Recipe)
        .where(models.Recipe.user_id == current_user.id)
        .options(_with_ingredients())
        .order_by(models.Recipe.name)
    )
    return [build_response(r) for r in result.scalars().all()]


@router.post("/", response_model=schemas.RecipeResponse, status_code=201)
async def create_recipe(
    data: schemas.RecipeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    dup = await db.execute(
        select(models.Recipe).where(
            models.Recipe.user_id == current_user.id,
            models.Recipe.name == data.name,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(400, "Receita com este nome já existe")

    recipe = models.Recipe(**data.model_dump(exclude={"ingredients"}), user_id=current_user.id)
    db.add(recipe)
    await db.flush()

    for ing in data.ingredients:
        ing_check = await db.execute(
            select(models.Ingredient).where(
                models.Ingredient.id == ing.ingredient_id,
                models.Ingredient.user_id == current_user.id,
            )
        )
        if not ing_check.scalar_one_or_none():
            raise HTTPException(404, f"Ingrediente ID {ing.ingredient_id} não encontrado")
        db.add(models.RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ing.ingredient_id,
            quantity=ing.quantity,
        ))

    await db.commit()

    result = await db.execute(
        select(models.Recipe)
        .where(models.Recipe.id == recipe.id)
        .options(_with_ingredients())
    )
    return build_response(result.scalar_one())


@router.get("/{recipe_id}", response_model=schemas.RecipeResponse)
async def get_recipe(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Recipe)
        .where(models.Recipe.id == recipe_id, models.Recipe.user_id == current_user.id)
        .options(_with_ingredients())
    )
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(404, "Receita não encontrada")
    return build_response(recipe)


@router.put("/{recipe_id}", response_model=schemas.RecipeResponse)
async def update_recipe(
    recipe_id: int,
    data: schemas.RecipeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Recipe)
        .where(models.Recipe.id == recipe_id, models.Recipe.user_id == current_user.id)
        .options(_with_ingredients())
    )
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(404, "Receita não encontrada")

    dup = await db.execute(
        select(models.Recipe).where(
            models.Recipe.user_id == current_user.id,
            models.Recipe.name == data.name,
            models.Recipe.id != recipe_id,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(400, "Receita com este nome já existe")

    for k, v in data.model_dump(exclude={"ingredients"}).items():
        setattr(recipe, k, v)

    for ri in list(recipe.recipe_ingredients):
        await db.delete(ri)
    await db.flush()

    for ing in data.ingredients:
        ing_check = await db.execute(
            select(models.Ingredient).where(
                models.Ingredient.id == ing.ingredient_id,
                models.Ingredient.user_id == current_user.id,
            )
        )
        if not ing_check.scalar_one_or_none():
            raise HTTPException(404, f"Ingrediente ID {ing.ingredient_id} não encontrado")
        db.add(models.RecipeIngredient(
            recipe_id=recipe_id,
            ingredient_id=ing.ingredient_id,
            quantity=ing.quantity,
        ))

    await db.commit()

    result = await db.execute(
        select(models.Recipe)
        .where(models.Recipe.id == recipe_id)
        .options(_with_ingredients())
    )
    return build_response(result.scalar_one())


@router.delete("/{recipe_id}", status_code=204)
async def delete_recipe(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Recipe).where(
            models.Recipe.id == recipe_id,
            models.Recipe.user_id == current_user.id,
        )
    )
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(404, "Receita não encontrada")
    await db.delete(recipe)
    await db.commit()
