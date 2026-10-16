import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
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
