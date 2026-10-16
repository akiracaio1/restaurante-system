from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, load_only
from typing import List

from database import get_db
from auth import get_current_user, get_operational_context, OperationalContext
import models
import schemas

router = APIRouter()


def _operational_options():
    """Carregamento enxuto, só com colunas liberadas ao papel restrito do banco.

    Usado pelo perfil Operação (e pela calculadora): nenhuma coluna de custo ou
    preço é sequer consultada.
    """
    R, RI, RS, I = models.Recipe, models.RecipeIngredient, models.RecipeSubRecipe, models.Ingredient
    return [
        selectinload(R.recipe_ingredients)
        .load_only(RI.id, RI.recipe_id, RI.ingredient_id, RI.quantity)
        .selectinload(RI.ingredient)
        .load_only(I.id, I.name, I.unit),
        selectinload(R.sub_recipes)
        .load_only(RS.id, RS.parent_recipe_id, RS.sub_recipe_id, RS.portions)
        .selectinload(RS.sub_recipe)
        .load_only(R.id, R.name),
        selectinload(R.proportion_base_ingredient).load_only(I.id, I.name, I.unit),
    ]


def _operational_columns():
    R = models.Recipe
    return (
        R.id, R.name, R.description, R.category, R.yield_portions, R.stock_unit,
        R.is_proportional, R.proportion_base_ingredient_id,
    )


def _operational_query():
    return select(models.Recipe).options(load_only(*_operational_columns()), *_operational_options())


def build_operacao_response(recipe: models.Recipe) -> schemas.RecipeOperacaoResponse:
    base = recipe.proportion_base_ingredient
    return schemas.RecipeOperacaoResponse(
        id=recipe.id,
        name=recipe.name,
        description=recipe.description,
        category=recipe.category,
        yield_portions=recipe.yield_portions,
        stock_unit=recipe.stock_unit or "porção",
        is_proportional=bool(recipe.is_proportional),
        proportion_base_ingredient_id=recipe.proportion_base_ingredient_id,
        proportion_base_ingredient_name=base.name if base else None,
        ingredients=[
            schemas.RecipeIngredientOperacaoResponse(
                ingredient_id=ri.ingredient_id,
                ingredient_name=ri.ingredient.name,
                ingredient_unit=ri.ingredient.unit,
                quantity=ri.quantity,
            )
            for ri in recipe.recipe_ingredients
        ],
        sub_recipes=[
            schemas.SubRecipeOperacaoResponse(
                id=sr.id,
                sub_recipe_id=sr.sub_recipe_id,
                sub_recipe_name=sr.sub_recipe.name,
                portions=sr.portions,
            )
            for sr in recipe.sub_recipes
        ],
    )


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
        stock_unit=recipe.stock_unit or "porção",
        min_stock=recipe.min_stock or 0.0,
        is_proportional=recipe.is_proportional,
        proportion_base_ingredient_id=recipe.proportion_base_ingredient_id,
        proportion_base_ingredient_name=(
            recipe.proportion_base_ingredient.name if recipe.proportion_base_ingredient else None
        ),
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
        selectinload(models.Recipe.proportion_base_ingredient),
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


# response_model=None: o formato depende do perfil (Master = completo, Operação =
# sem nenhum campo financeiro). Cada perfil devolve a sua própria classe.
@router.get("/", response_model=None)
async def list_recipes(ctx: OperationalContext = Depends(get_operational_context)):
    if ctx.is_master:
        result = await ctx.db.execute(
            select(models.Recipe)
            .where(models.Recipe.user_id == ctx.account_id)
            .options(*_eager_options())
            .order_by(models.Recipe.name)
        )
        return [build_response(r) for r in result.scalars().all()]

    result = await ctx.db.execute(
        _operational_query()
        .where(models.Recipe.user_id == ctx.account_id)
        .order_by(models.Recipe.name)
    )
    return [build_operacao_response(r) for r in result.scalars().all()]


def _validate_proportion(data: schemas.RecipeBase, ingredients: List[schemas.RecipeIngredientInput]):
    if not data.is_proportional:
        return
    if not data.proportion_base_ingredient_id:
        raise HTTPException(400, "Selecione o ingrediente base da calculadora de proporção")
    if not any(i.ingredient_id == data.proportion_base_ingredient_id for i in ingredients):
        raise HTTPException(400, "O ingrediente base precisa estar na lista de ingredientes da receita")


@router.post("/", response_model=schemas.RecipeResponse, status_code=201)
async def create_recipe(
    data: schemas.RecipeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _validate_proportion(data, data.ingredients)

    dup = await db.execute(
        select(models.Recipe).where(
            models.Recipe.user_id == current_user.account_id,
            models.Recipe.name == data.name,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(400, "Receita com este nome já existe")

    recipe = models.Recipe(**data.model_dump(exclude={"ingredients"}), user_id=current_user.account_id)
    db.add(recipe)
    await db.flush()

    for ing in data.ingredients:
        ing_check = await db.execute(
            select(models.Ingredient).where(
                models.Ingredient.id == ing.ingredient_id,
                models.Ingredient.user_id == current_user.account_id,
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


@router.get("/{recipe_id}", response_model=None)
async def get_recipe(
    recipe_id: int,
    ctx: OperationalContext = Depends(get_operational_context),
):
    if ctx.is_master:
        result = await ctx.db.execute(
            select(models.Recipe)
            .where(models.Recipe.id == recipe_id, models.Recipe.user_id == ctx.account_id)
            .options(*_eager_options())
        )
        recipe = result.scalar_one_or_none()
        if not recipe:
            raise HTTPException(404, "Receita não encontrada")
        return build_response(recipe)

    result = await ctx.db.execute(
        _operational_query().where(
            models.Recipe.id == recipe_id, models.Recipe.user_id == ctx.account_id
        )
    )
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(404, "Receita não encontrada")
    return build_operacao_response(recipe)


@router.put("/{recipe_id}", response_model=schemas.RecipeResponse)
async def update_recipe(
    recipe_id: int,
    data: schemas.RecipeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Recipe)
        .where(models.Recipe.id == recipe_id, models.Recipe.user_id == current_user.account_id)
        .options(*_eager_options())
    )
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(404, "Receita não encontrada")

    _validate_proportion(data, data.ingredients)

    dup = await db.execute(
        select(models.Recipe).where(
            models.Recipe.user_id == current_user.account_id,
            models.Recipe.name == data.name,
            models.Recipe.id != recipe_id,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(400, "Receita com este nome já existe")

    fields = data.model_dump(exclude={"ingredients"})
    if "min_stock" not in data.model_fields_set:
        fields.pop("min_stock")  # cliente antigo que não envia o campo não zera o mínimo
    for k, v in fields.items():
        setattr(recipe, k, v)

    for ri in list(recipe.recipe_ingredients):
        recipe.recipe_ingredients.remove(ri)

    for ing in data.ingredients:
        ing_check = await db.execute(
            select(models.Ingredient).where(
                models.Ingredient.id == ing.ingredient_id,
                models.Ingredient.user_id == current_user.account_id,
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
            models.Recipe.user_id == current_user.account_id,
        )
    )
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(404, "Receita não encontrada")
    await db.delete(recipe)
    await db.commit()


@router.put("/{recipe_id}/unidade-estoque", response_model=schemas.RecipeResponse)
async def update_stock_unit(
    recipe_id: int,
    data: schemas.RecipeStockUnitInput,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Recipe).where(
            models.Recipe.id == recipe_id,
            models.Recipe.user_id == current_user.account_id,
        )
    )
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(404, "Receita não encontrada")

    unit = data.stock_unit.strip()
    if not unit:
        raise HTTPException(400, "Unidade de estoque não pode ser vazia")
    recipe.stock_unit = unit
    await db.commit()

    result = await db.execute(
        select(models.Recipe).where(models.Recipe.id == recipe_id).options(*_eager_options())
    )
    return build_response(result.scalar_one())


@router.put("/{recipe_id}/estoque-minimo", response_model=schemas.RecipeResponse)
async def update_min_stock(
    recipe_id: int,
    data: schemas.RecipeMinStockInput,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Recipe).where(
            models.Recipe.id == recipe_id,
            models.Recipe.user_id == current_user.account_id,
        )
    )
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(404, "Receita não encontrada")
    recipe.min_stock = data.min_stock
    await db.commit()

    result = await db.execute(
        select(models.Recipe).where(models.Recipe.id == recipe_id).options(*_eager_options())
    )
    return build_response(result.scalar_one())


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
            models.Recipe.user_id == current_user.account_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Receita não encontrada")

    if data.sub_recipe_id == recipe_id:
        raise HTTPException(400, "Uma receita não pode ser sub-receita de si mesma")

    result = await db.execute(
        select(models.Recipe).where(
            models.Recipe.id == data.sub_recipe_id,
            models.Recipe.user_id == current_user.account_id,
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
            models.Recipe.user_id == current_user.account_id,
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
            models.Recipe.user_id == current_user.account_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Receita não encontrada")

    result = await db.execute(
        select(models.SalesChannel).where(
            models.SalesChannel.id == channel_id,
            models.SalesChannel.user_id == current_user.account_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Canal de venda não encontrado")

    for ei in data.extra_ingredients:
        ing_check = await db.execute(
            select(models.Ingredient).where(
                models.Ingredient.id == ei.ingredient_id,
                models.Ingredient.user_id == current_user.account_id,
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
            models.Recipe.user_id == current_user.account_id,
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


@router.post("/{recipe_id}/calcular-proporcao", response_model=schemas.ProportionCalculateResponse)
async def calculate_proportion(
    recipe_id: int,
    data: schemas.ProportionCalculateInput,
    ctx: OperationalContext = Depends(get_operational_context),
):
    # Carregamento enxuto para os dois perfis: a calculadora só usa nomes,
    # unidades e quantidades, nunca custos.
    result = await ctx.db.execute(
        _operational_query().where(
            models.Recipe.id == recipe_id, models.Recipe.user_id == ctx.account_id
        )
    )
    recipe = result.scalar_one_or_none()
    if not recipe:
        raise HTTPException(404, "Receita não encontrada")

    if not recipe.is_proportional or not recipe.proportion_base_ingredient_id:
        raise HTTPException(400, "Esta receita não tem a calculadora de proporção habilitada")

    if data.base_quantity <= 0:
        raise HTTPException(400, "Informe uma quantidade maior que zero")

    base_ri = next(
        (ri for ri in recipe.recipe_ingredients if ri.ingredient_id == recipe.proportion_base_ingredient_id),
        None,
    )
    if not base_ri or base_ri.quantity <= 0:
        raise HTTPException(400, "Ingrediente base não encontrado na receita")

    scale = data.base_quantity / base_ri.quantity

    ingredients_resp = [
        schemas.ProportionIngredientResult(
            ingredient_id=ri.ingredient_id,
            ingredient_name=ri.ingredient.name,
            unit=ri.ingredient.unit,
            base_quantity=ri.quantity,
            calculated_quantity=round(ri.quantity * scale, 3),
        )
        for ri in recipe.recipe_ingredients
    ]

    return schemas.ProportionCalculateResponse(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        base_ingredient_id=base_ri.ingredient_id,
        base_ingredient_name=base_ri.ingredient.name,
        base_ingredient_unit=base_ri.ingredient.unit,
        scale_factor=round(scale, 6),
        base_yield=recipe.yield_portions,
        calculated_yield=round(recipe.yield_portions * scale, 2),
        yield_unit=recipe.stock_unit or "porção",
        ingredients=ingredients_resp,
    )
