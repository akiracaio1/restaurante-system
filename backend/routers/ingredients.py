import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database import get_db
from auth import get_current_user, get_operational_context, OperationalContext
import models
import schemas

router = APIRouter()


def _parse_stages(raw):
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw not in ('null', ''):
        return json.loads(raw)
    return []


def _operacao_columns():
    # Somente colunas liberadas ao papel restrito do banco (ver rbac_db.py).
    I = models.Ingredient
    return (I.id, I.name, I.unit, I.yield_percentage, I.reduction_stages)


def _to_operacao_response(row) -> schemas.IngredientOperacaoResponse:
    return schemas.IngredientOperacaoResponse(
        id=row.id,
        name=row.name,
        unit=row.unit,
        yield_percentage=row.yield_percentage if row.yield_percentage is not None else 100.0,
        reduction_stages=_parse_stages(row.reduction_stages),
    )


def _to_response(obj: models.Ingredient) -> schemas.IngredientResponse:
    return schemas.IngredientResponse(
        id=obj.id,
        name=obj.name,
        unit=obj.unit,
        unit_cost=obj.unit_cost,
        min_stock=obj.min_stock,
        purchase_unit=obj.purchase_unit,
        purchase_quantity=obj.purchase_quantity,
        purchase_cost=obj.purchase_cost,
        yield_percentage=obj.yield_percentage,
        reduction_stages=_parse_stages(obj.reduction_stages),
        real_unit_cost=obj.real_unit_cost,
        processing_cost_per_unit=obj.processing_cost_per_unit,
        processing_cost_per_batch=obj.processing_cost_per_batch,
        processing_batch_size=obj.processing_batch_size,
    )


# response_model=None: o formato depende do perfil (Master = completo, Operação =
# sem nenhum campo financeiro). Cada perfil devolve a sua própria classe.
@router.get("/", response_model=None)
async def list_ingredients(ctx: OperationalContext = Depends(get_operational_context)):
    if ctx.is_master:
        result = await ctx.db.execute(
            select(models.Ingredient)
            .where(models.Ingredient.user_id == ctx.account_id)
            .order_by(models.Ingredient.name)
        )
        return [_to_response(i) for i in result.scalars().all()]

    result = await ctx.db.execute(
        select(*_operacao_columns())
        .where(models.Ingredient.user_id == ctx.account_id)
        .order_by(models.Ingredient.name)
    )
    return [_to_operacao_response(r) for r in result.all()]


@router.post("/", response_model=schemas.IngredientResponse, status_code=201)
async def create_ingredient(
    data: schemas.IngredientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    dup = await db.execute(
        select(models.Ingredient).where(
            models.Ingredient.user_id == current_user.account_id,
            models.Ingredient.name == data.name,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(400, "Ingrediente com este nome já existe")
    obj = models.Ingredient(**data.model_dump(), user_id=current_user.account_id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return _to_response(obj)


@router.get("/{ingredient_id}", response_model=None)
async def get_ingredient(
    ingredient_id: int,
    ctx: OperationalContext = Depends(get_operational_context),
):
    if ctx.is_master:
        result = await ctx.db.execute(
            select(models.Ingredient).where(
                models.Ingredient.id == ingredient_id,
                models.Ingredient.user_id == ctx.account_id,
            )
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise HTTPException(404, "Ingrediente não encontrado")
        return _to_response(obj)

    result = await ctx.db.execute(
        select(*_operacao_columns()).where(
            models.Ingredient.id == ingredient_id,
            models.Ingredient.user_id == ctx.account_id,
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Ingrediente não encontrado")
    return _to_operacao_response(row)


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
            models.Ingredient.user_id == current_user.account_id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Ingrediente não encontrado")
    dup = await db.execute(
        select(models.Ingredient).where(
            models.Ingredient.user_id == current_user.account_id,
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
    return _to_response(obj)


@router.delete("/{ingredient_id}", status_code=204)
async def delete_ingredient(
    ingredient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Ingredient).where(
            models.Ingredient.id == ingredient_id,
            models.Ingredient.user_id == current_user.account_id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Ingrediente não encontrado")

    in_use_checks = [
        (models.RecipeIngredient, "está sendo usado em uma ou mais receitas"),
        (models.RecipeChannelIngredient, "está sendo usado como custo extra em uma ou mais modalidades de venda"),
        (models.PurchaseItem, "possui compras registradas no histórico"),
        (models.Stock, "possui estoque registrado"),
        (models.StockMovement, "possui movimentações de estoque registradas"),
    ]
    for model_cls, reason in in_use_checks:
        check = await db.execute(
            select(model_cls).where(model_cls.ingredient_id == ingredient_id).limit(1)
        )
        if check.scalar_one_or_none():
            raise HTTPException(
                400,
                f"Ingrediente não pode ser excluído: {reason}. Remova essas referências primeiro.",
            )

    await db.delete(obj)
    await db.commit()


def _fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", ",") or "0"


@router.post("/{target_id}/mesclar", response_model=schemas.IngredientMergeResponse)
async def merge_ingredients(
    target_id: int,
    data: schemas.IngredientMergeInput,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Mescla o ingrediente `source_id` (duplicado, será removido) em `target_id` (permanece).

    Tudo o que apontava para o duplicado passa a apontar para o que fica: receitas,
    custos extras de canais, compras, estoque e histórico. Tudo ou nada.
    Com dry_run=true calcula o resumo e desfaz, sem gravar nada.
    """
    if data.source_id == target_id:
        raise HTTPException(400, "Escolha dois ingredientes diferentes")
    account = current_user.account_id

    rows = await db.execute(
        select(models.Ingredient).where(
            models.Ingredient.id.in_([target_id, data.source_id]),
            models.Ingredient.user_id == account,
        )
    )
    found = {i.id: i for i in rows.scalars().all()}
    if target_id not in found or data.source_id not in found:
        raise HTTPException(404, "Ingrediente não encontrado")
    target, source = found[target_id], found[data.source_id]
    if (source.unit or "").strip().lower() != (target.unit or "").strip().lower():
        raise HTTPException(
            400,
            f"Unidades diferentes ({source.unit} e {target.unit}). Ajuste a unidade para ser a mesma antes de mesclar.",
        )

    pair = [target.id, source.id]

    # Receitas: quem usava só o duplicado passa a usar o que fica; quem usava os dois soma as quantidades.
    ris = (await db.execute(
        select(models.RecipeIngredient).where(models.RecipeIngredient.ingredient_id.in_(pair))
    )).scalars().all()
    by_recipe: dict[int, dict[int, models.RecipeIngredient]] = {}
    for ri in ris:
        by_recipe.setdefault(ri.recipe_id, {})[ri.ingredient_id] = ri
    recipe_names = {
        r.id: r.name
        for r in (await db.execute(
            select(models.Recipe).where(models.Recipe.id.in_(list(by_recipe) or [0]), models.Recipe.user_id == account)
        )).scalars().all()
    }
    moved, combined = [], []
    for recipe_id, items in by_recipe.items():
        if recipe_id not in recipe_names or source.id not in items:
            continue
        if target.id in items:
            items[target.id].quantity += items[source.id].quantity
            await db.delete(items[source.id])
            combined.append(recipe_names[recipe_id])
        else:
            items[source.id].ingredient_id = target.id
            moved.append(recipe_names[recipe_id])

    # Custos extras das modalidades de venda: mesma regra.
    extras = (await db.execute(
        select(models.RecipeChannelIngredient).where(models.RecipeChannelIngredient.ingredient_id.in_(pair))
    )).scalars().all()
    by_price: dict[int, dict[int, models.RecipeChannelIngredient]] = {}
    for ex in extras:
        by_price.setdefault(ex.recipe_channel_price_id, {})[ex.ingredient_id] = ex
    channels_updated = 0
    for items in by_price.values():
        if source.id not in items:
            continue
        channels_updated += 1
        if target.id in items:
            items[target.id].quantity += items[source.id].quantity
            await db.delete(items[source.id])
        else:
            items[source.id].ingredient_id = target.id

    # Ingrediente-base da calculadora de proporção.
    base_recipes = [
        r.name for r in (await db.execute(
            select(models.Recipe).where(
                models.Recipe.proportion_base_ingredient_id == source.id, models.Recipe.user_id == account
            )
        )).scalars().all()
    ]
    await db.execute(
        update(models.Recipe)
        .where(models.Recipe.proportion_base_ingredient_id == source.id, models.Recipe.user_id == account)
        .values(proportion_base_ingredient_id=target.id)
    )

    # Histórico de compras e de movimentações de estoque.
    purchases = await db.execute(
        update(models.PurchaseItem).where(models.PurchaseItem.ingredient_id == source.id).values(ingredient_id=target.id)
    )
    movements = await db.execute(
        update(models.StockMovement)
        .where(models.StockMovement.ingredient_id == source.id, models.StockMovement.user_id == account)
        .values(ingredient_id=target.id)
    )

    # Estoque: as quantidades se somam.
    stocks = {
        s.ingredient_id: s
        for s in (await db.execute(
            select(models.Stock).where(models.Stock.user_id == account, models.Stock.ingredient_id.in_(pair))
        )).scalars().all()
    }
    before_target = stocks[target.id].quantity if target.id in stocks else 0.0
    before_source = stocks[source.id].quantity if source.id in stocks else 0.0
    total = before_target + before_source
    now = datetime.utcnow()
    if source.id in stocks:
        if target.id in stocks:
            stocks[target.id].quantity, stocks[target.id].updated_at = total, now
            await db.delete(stocks[source.id])
        else:
            stocks[source.id].ingredient_id = target.id
            stocks[source.id].updated_at = now
        if before_source:
            db.add(models.StockMovement(
                user_id=account, ingredient_id=target.id, type="ajuste", quantity=total, reason="mescla",
                notes=f"Mesclado com '{source.name}': {_fmt(before_target)} + {_fmt(before_source)} = {_fmt(total)}",
            ))

    if not target.min_stock and source.min_stock:
        target.min_stock = source.min_stock

    summary = schemas.IngredientMergeResponse(
        dry_run=data.dry_run,
        target_id=target.id, target_name=target.name, source_id=source.id, source_name=source.name, unit=target.unit,
        recipes_moved=sorted(moved), recipes_combined=sorted(combined),
        channel_prices_updated=channels_updated,
        purchase_items_moved=purchases.rowcount or 0, movements_moved=movements.rowcount or 0,
        stock_target_before=before_target, stock_source_before=before_source, stock_after=total,
        base_recipes=sorted(base_recipes),
    )

    await db.flush()
    await db.delete(source)
    if data.dry_run:
        await db.rollback()
    else:
        await db.commit()
    return summary
