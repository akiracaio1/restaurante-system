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

    sub_recipes_resp = []
    for sr in recipe.sub_recipes:
        sub_ing_cost = sum(
            ri.ingredient.real_unit_cost * ri.quantity
            for ri in sr.sub_recipe.recipe_ingredients
        )
        cpp = (sub_ing_cost / sr.sub_recipe.yield_portions) if sr.sub_recipe.yield_portions > 0 else 0.0
        subtotal = cpp * sr.portions
        total_cost += subtotal
        sub_recipes_resp.append(
            schemas.SubRecipeResponse(
                id=sr.id,
                sub_recipe_id=sr.sub_recipe_id,
                sub_recipe_name=sr.sub_recipe.name,
                portions=sr.portions,
                cost_per_portion=round(cpp, 4),
                subtotal=round(subtotal, 4),
            )
        )

    cost_per_portion = (total_cost / recipe.yield_portions) if recipe.yield_portions > 0 else 0.0
    cmv = (cost_per_portion / recipe.sale_price * 100) if recipe.sale_price > 0 else 0.0

    channel_prices_resp = []
    for cp in recipe.channel_prices:
        extra_cost = 0.0
        extra_resp = []
        for ei in cp.extra_ingredients:
            real_cost = ei.ingredient.real_unit_cost
            subtotal = real_cost * ei.quantity
            extra_cost += subtotal
            extra_resp.append(
                schemas.ChannelExtraIngredientResponse(
                    id=ei.id,
                    ingredient_id=ei.ingredient_id,
                    ingredient_name=ei.ingredient.name,
                    ingredient_unit=ei.ingredient.unit,
                    quantity=ei.quantity,
                    subtotal=round(subtotal, 4),
                )
            )
        fee = (cp.channel.fee_percent / 100 * cp.sale_price) if cp.channel.fee_percent else 0.0
        fixed = cp.channel.fixed_cost or 0.0
        channel_total_cost = cost_per_portion + extra_cost + fee + fixed
        channel_cmv = (channel_total_cost / cp.sale_price * 100) if cp.sale_price > 0 else 0.0
        channel_prices_resp.append(
            schemas.RecipeChannelPriceResponse(
                id=cp.id,
                channel_id=cp.channel_id,
                channel_name=cp.channel.name,
                fee_percent=cp.channel.fee_percent,
                fixed_cost=cp.channel.fixed_cost,
                sale_price=cp.sale_price,
                extra_ingredients=extra_resp,
                extra_cost=round(extra_cost, 4),
                total_cost=round(channel_total_cost, 4),
                cmv_percent=round(channel_cmv, 2),
            )
        )

    return schemas.RecipeResponse(
        id=recipe.id,
        name=recipe.name,
        description=recipe.description,
        category=recipe.category,
        sale_price=recipe.sale_price,
        yield_portions=recipe.yield_portions,
        ingredients=ingredients_resp,
        sub_recipes=sub_recipes_resp,
        channel_prices=channel_prices_resp,
        total_cost=round(total_cost, 4),
        cmv_percent=round(cmv, 2),
    )


def _eager_options():
    return [
        selectinload(models.Recipe.recipe_ingredients).selectinload(
            models.RecipeIngredient.ingredient
        ),
        selectinload(models.Recipe.sub_recipes)
            .selectinload(models.RecipeSubRecipe.sub_recipe)
            .selectinload(models.Recipe.recipe_ingredients)
            .selectinload(models.RecipeIngredient.ingredient),
        selectinload(models.Recipe.channel_prices)
            .selectinload(models.RecipeChannelPrice.channel),
        selectinload(models.Recipe.channel_prices)
            .selectinload(models.RecipeChannelPrice.extra_ingredients)
            .selectinload(models.RecipeChannelIngredient.ingredient),
    ]


@router.get("/", response_model=List[schemas.RecipeResponse])
async def list_recipes(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Recipe)
        .where(models.Recipe.user_id == current_user.id)
        .options(*_eager_options())
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
        .options(*_eager_options())
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
        .options(*_eager_options())
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
        .options(*_eager_options())
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
        recipe.recipe_ingredients.remove(ri)

    for ing in data.ingredients:
        ing_check = await db.execute(
            select(models.Ingredient).where(
                models.Ingredient.id == ing.ingredient_id,
                models.Ingredient.user_id == current_user.id,
            )
        )
        if not ing_check.scalar_one_or_none():
            raise HTTPException(404, f"Ingrediente ID {ing.ingredient_id} não encontrado")
        recipe.recipe_ingredients.append(models.RecipeIngredient(
            ingredient_id=ing.ingredient_id,
            quantity=ing.quantity,
        ))

    await db.commit()

    result = await db.execute(
        select(models.Recipe)
        .where(models.Recipe.id == recipe_id)
        .options(*_eager_options())
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


@router.post("/{recipe_id}/sub-receitas", response_model=schemas.RecipeResponse, status_code=201)
async def add_sub_recipe(
    recipe_id: int,
    data: schemas.SubRecipeInput,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Recipe).where(
            models.Recipe.id == recipe_id,
            models.Recipe.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Receita não encontrada")

    if data.sub_recipe_id == recipe_id:
        raise HTTPException(400, "Uma receita não pode ser sub-receita de si mesma")

    result = await db.execute(
        select(models.Recipe).where(
            models.Recipe.id == data.sub_recipe_id,
            models.Recipe.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, f"Sub-receita ID {data.sub_recipe_id} não encontrada")

    db.add(models.RecipeSubRecipe(
        parent_recipe_id=recipe_id,
        sub_recipe_id=data.sub_recipe_id,
        portions=data.portions,
    ))
    await db.commit()

    result = await db.execute(
        select(models.Recipe).where(models.Recipe.id == recipe_id).options(*_eager_options())
    )
    return build_response(result.scalar_one())


@router.delete("/{recipe_id}/sub-receitas/{entry_id}", status_code=204)
async def remove_sub_recipe(
    recipe_id: int,
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Recipe).where(
            models.Recipe.id == recipe_id,
            models.Recipe.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Receita não encontrada")

    result = await db.execute(
        select(models.RecipeSubRecipe).where(
            models.RecipeSubRecipe.id == entry_id,
            models.RecipeSubRecipe.parent_recipe_id == recipe_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Sub-receita não encontrada")

    await db.delete(entry)
    await db.commit()


@router.put("/{recipe_id}/canais/{channel_id}", response_model=schemas.RecipeResponse)
async def set_channel_price(
    recipe_id: int,
    channel_id: int,
    data: schemas.RecipeChannelPriceInput,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Recipe).where(
            models.Recipe.id == recipe_id,
            models.Recipe.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Receita não encontrada")

    result = await db.execute(
        select(models.SalesChannel).where(
            models.SalesChannel.id == channel_id,
            models.SalesChannel.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Canal de venda não encontrado")

    for ei in data.extra_ingredients:
        ing_check = await db.execute(
            select(models.Ingredient).where(
                models.Ingredient.id == ei.ingredient_id,
                models.Ingredient.user_id == current_user.id,
            )
        )
        if not ing_check.scalar_one_or_none():
            raise HTTPException(404, f"Ingrediente ID {ei.ingredient_id} não encontrado")

    result = await db.execute(
        select(models.RecipeChannelPrice)
        .where(
            models.RecipeChannelPrice.recipe_id == recipe_id,
            models.RecipeChannelPrice.channel_id == channel_id,
        )
        .options(selectinload(models.RecipeChannelPrice.extra_ingredients))
    )
    channel_price = result.scalar_one_or_none()

    if channel_price:
        channel_price.sale_price = data.sale_price
        for ei in list(channel_price.extra_ingredients):
            channel_price.extra_ingredients.remove(ei)
    else:
        channel_price = models.RecipeChannelPrice(
            recipe_id=recipe_id, channel_id=channel_id, sale_price=data.sale_price
        )
        db.add(channel_price)

    for ei in data.extra_ingredients:
        channel_price.extra_ingredients.append(models.RecipeChannelIngredient(
            ingredient_id=ei.ingredient_id,
            quantity=ei.quantity,
        ))

    await db.commit()

    result = await db.execute(
        select(models.Recipe).where(models.Recipe.id == recipe_id).options(*_eager_options())
    )
    return build_response(result.scalar_one())


@router.delete("/{recipe_id}/canais/{channel_id}", status_code=204)
async def remove_channel_price(
    recipe_id: int,
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Recipe).where(
            models.Recipe.id == recipe_id,
            models.Recipe.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Receita não encontrada")

    result = await db.execute(
        select(models.RecipeChannelPrice).where(
            models.RecipeChannelPrice.recipe_id == recipe_id,
            models.RecipeChannelPrice.channel_id == channel_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Preço de canal não encontrado")

    await db.delete(entry)
    await db.commit()
