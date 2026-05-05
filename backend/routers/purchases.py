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


def _item_to_response(item: models.PurchaseItem) -> schemas.PurchaseItemResponse:
    return schemas.PurchaseItemResponse(
        id=item.id,
        ingredient_id=item.ingredient_id,
        ingredient_name=item.ingredient.name if item.ingredient else '',
        quantity=item.quantity,
        unit=item.unit,
        total_price=item.total_price,
        unit_cost=item.unit_cost,
        previous_unit_cost=item.previous_unit_cost,
        notes=item.notes,
    )


def _to_response(purchase: models.Purchase) -> schemas.PurchaseResponse:
    items = [_item_to_response(i) for i in purchase.items]
    total = sum(i.total_price for i in purchase.items)
    return schemas.PurchaseResponse(
        id=purchase.id,
        date=purchase.date,
        supplier=purchase.supplier,
        location=purchase.location,
        notes=purchase.notes,
        created_at=purchase.created_at,
        items=items,
        total=total,
    )


@router.get("/", response_model=List[schemas.PurchaseResponse])
async def list_purchases(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Purchase)
        .where(models.Purchase.user_id == current_user.id)
        .options(
            selectinload(models.Purchase.items).selectinload(models.PurchaseItem.ingredient)
        )
        .order_by(models.Purchase.date.desc())
    )
    return [_to_response(p) for p in result.scalars().all()]


@router.post("/", response_model=schemas.PurchaseResponse, status_code=201)
async def create_purchase(
    data: schemas.PurchaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not data.items:
        raise HTTPException(400, "A compra deve ter pelo menos um item")

    purchase = models.Purchase(
        user_id=current_user.id,
        date=data.date,
        supplier=data.supplier,
        location=data.location,
        notes=data.notes,
    )
    db.add(purchase)
    await db.flush()

    for item_data in data.items:
        ing_result = await db.execute(
            select(models.Ingredient).where(
                models.Ingredient.id == item_data.ingredient_id,
                models.Ingredient.user_id == current_user.id,
            )
        )
        ingredient = ing_result.scalar_one_or_none()
        if not ingredient:
            raise HTTPException(404, f"Ingrediente {item_data.ingredient_id} não encontrado")

        unit_cost = item_data.total_price / item_data.quantity
        previous_unit_cost = ingredient.unit_cost

        item = models.PurchaseItem(
            purchase_id=purchase.id,
            ingredient_id=item_data.ingredient_id,
            quantity=item_data.quantity,
            unit=item_data.unit,
            total_price=item_data.total_price,
            unit_cost=unit_cost,
            previous_unit_cost=previous_unit_cost,
            notes=item_data.notes,
        )
        db.add(item)
        await db.flush()

        ingredient.unit_cost = unit_cost

        stock_result = await db.execute(
            select(models.Stock).where(
                models.Stock.user_id == current_user.id,
                models.Stock.ingredient_id == item_data.ingredient_id,
            )
        )
        stock = stock_result.scalar_one_or_none()
        if stock:
            stock.quantity += item_data.quantity
            stock.updated_at = datetime.utcnow()
        else:
            stock = models.Stock(
                user_id=current_user.id,
                ingredient_id=item_data.ingredient_id,
                quantity=item_data.quantity,
                updated_at=datetime.utcnow(),
            )
            db.add(stock)

        movement = models.StockMovement(
            user_id=current_user.id,
            ingredient_id=item_data.ingredient_id,
            type='entrada',
            quantity=item_data.quantity,
            reason='compra',
            purchase_item_id=item.id,
            notes=item_data.notes,
        )
        db.add(movement)

    await db.commit()

    result = await db.execute(
        select(models.Purchase)
        .where(models.Purchase.id == purchase.id)
        .options(
            selectinload(models.Purchase.items).selectinload(models.PurchaseItem.ingredient)
        )
    )
    return _to_response(result.scalar_one())


# /historico/ must be registered before /{purchase_id} to avoid int-parse conflicts
@router.get("/historico/{ingredient_id}", response_model=List[schemas.PurchaseItemHistoryResponse])
async def ingredient_purchase_history(
    ingredient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.PurchaseItem)
        .join(models.Purchase, models.PurchaseItem.purchase_id == models.Purchase.id)
        .where(
            models.Purchase.user_id == current_user.id,
            models.PurchaseItem.ingredient_id == ingredient_id,
        )
        .options(
            selectinload(models.PurchaseItem.ingredient),
            selectinload(models.PurchaseItem.purchase),
        )
        .order_by(models.Purchase.date.asc())
    )
    items = result.scalars().all()
    return [
        schemas.PurchaseItemHistoryResponse(
            id=i.id,
            ingredient_id=i.ingredient_id,
            ingredient_name=i.ingredient.name if i.ingredient else '',
            quantity=i.quantity,
            unit=i.unit,
            total_price=i.total_price,
            unit_cost=i.unit_cost,
            previous_unit_cost=i.previous_unit_cost,
            notes=i.notes,
            purchase_date=i.purchase.date,
            supplier=i.purchase.supplier,
            location=i.purchase.location,
        )
        for i in items
    ]


@router.get("/{purchase_id}", response_model=schemas.PurchaseResponse)
async def get_purchase(
    purchase_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Purchase)
        .where(
            models.Purchase.id == purchase_id,
            models.Purchase.user_id == current_user.id,
        )
        .options(
            selectinload(models.Purchase.items).selectinload(models.PurchaseItem.ingredient)
        )
    )
    purchase = result.scalar_one_or_none()
    if not purchase:
        raise HTTPException(404, "Compra não encontrada")
    return _to_response(purchase)


@router.delete("/{purchase_id}", status_code=204)
async def delete_purchase(
    purchase_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Purchase).where(
            models.Purchase.id == purchase_id,
            models.Purchase.user_id == current_user.id,
        )
    )
    purchase = result.scalar_one_or_none()
    if not purchase:
        raise HTTPException(404, "Compra não encontrada")
    await db.delete(purchase)
    await db.commit()
