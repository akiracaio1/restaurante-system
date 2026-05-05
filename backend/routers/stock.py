from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime

from database import get_db
from auth import get_current_user
import models
import schemas

router = APIRouter()


def _to_response(stock: models.Stock) -> schemas.StockResponse:
    return schemas.StockResponse(
        id=stock.id,
        ingredient_id=stock.ingredient_id,
        ingredient_name=stock.ingredient.name if stock.ingredient else '',
        unit=stock.ingredient.unit if stock.ingredient else '',
        quantity=stock.quantity,
        min_stock=stock.ingredient.min_stock if stock.ingredient else 0.0,
        updated_at=stock.updated_at,
    )


@router.get("/", response_model=List[schemas.StockResponse])
async def list_stock(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Stock)
        .where(models.Stock.user_id == current_user.id)
        .options(selectinload(models.Stock.ingredient))
        .order_by(models.Stock.ingredient_id)
    )
    return [_to_response(s) for s in result.scalars().all()]


# /movimentacoes/ must be before /{ingredient_id} to avoid routing conflicts
@router.get("/movimentacoes/{ingredient_id}", response_model=List[schemas.StockMovementResponse])
async def list_movements(
    ingredient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.StockMovement)
        .where(
            models.StockMovement.user_id == current_user.id,
            models.StockMovement.ingredient_id == ingredient_id,
        )
        .options(selectinload(models.StockMovement.ingredient))
        .order_by(models.StockMovement.created_at.desc())
    )
    movements = result.scalars().all()
    return [
        schemas.StockMovementResponse(
            id=m.id,
            type=m.type,
            quantity=m.quantity,
            reason=m.reason,
            notes=m.notes,
            created_at=m.created_at,
            ingredient_name=m.ingredient.name if m.ingredient else '',
        )
        for m in movements
    ]


@router.put("/{ingredient_id}", response_model=schemas.StockResponse)
async def adjust_stock(
    ingredient_id: int,
    data: schemas.StockAdjustInput,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    stock_result = await db.execute(
        select(models.Stock)
        .where(
            models.Stock.user_id == current_user.id,
            models.Stock.ingredient_id == ingredient_id,
        )
    )
    stock = stock_result.scalar_one_or_none()

    if not stock:
        ing_result = await db.execute(
            select(models.Ingredient).where(
                models.Ingredient.id == ingredient_id,
                models.Ingredient.user_id == current_user.id,
            )
        )
        if not ing_result.scalar_one_or_none():
            raise HTTPException(404, "Ingrediente não encontrado")
        stock = models.Stock(
            user_id=current_user.id,
            ingredient_id=ingredient_id,
            quantity=data.quantity,
            updated_at=datetime.utcnow(),
        )
        db.add(stock)
    else:
        stock.quantity = data.quantity
        stock.updated_at = datetime.utcnow()

    movement = models.StockMovement(
        user_id=current_user.id,
        ingredient_id=ingredient_id,
        type='ajuste',
        quantity=data.quantity,
        reason='ajuste_manual',
        notes=data.notes,
    )
    db.add(movement)
    await db.commit()

    result = await db.execute(
        select(models.Stock)
        .where(
            models.Stock.user_id == current_user.id,
            models.Stock.ingredient_id == ingredient_id,
        )
        .options(selectinload(models.Stock.ingredient))
    )
    return _to_response(result.scalar_one())
