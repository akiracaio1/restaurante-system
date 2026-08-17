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

_UNIT_CONVERSIONS: dict[tuple[str, str], float] = {
    ('kg', 'g'):  1000.0,
    ('g',  'kg'): 0.001,
    ('L',  'ml'): 1000.0,
    ('ml', 'L'):  0.001,
}


def convert_to_base(quantity: float, from_unit: str, to_unit: str) -> float:
    if from_unit == to_unit:
        return quantity
    factor = _UNIT_CONVERSIONS.get((from_unit, to_unit))
    return quantity * factor if factor is not None else quantity


def _item_to_response(item: models.PurchaseItem) -> schemas.PurchaseItemResponse:
    return schemas.PurchaseItemResponse(
        id=item.id,
        ingredient_id=item.ingredient_id,
        ingredient_name=item.ingredient.name if item.ingredient else '',
        quantity=item.quantity,
        unit=item.unit,
        total_price=item.total_price,
        allocated_extra=item.allocated_extra,
        unit_cost=item.unit_cost,
        previous_unit_cost=item.previous_unit_cost,
        notes=item.notes,
    )


def _to_response(purchase: models.Purchase) -> schemas.PurchaseResponse:
    items = [_item_to_response(i) for i in purchase.items]
    subtotal = sum(i.total_price for i in purchase.items)
    supplier_name = purchase.supplier_entity.name if purchase.supplier_entity else purchase.supplier
    return schemas.PurchaseResponse(
        id=purchase.id,
        date=purchase.date,
        supplier=supplier_name,
        supplier_id=purchase.supplier_id,
        location=purchase.location,
        notes=purchase.notes,
        created_at=purchase.created_at,
        tax=purchase.tax or 0.0,
        freight=purchase.freight or 0.0,
        items=items,
        subtotal=subtotal,
        total=subtotal + (purchase.tax or 0.0) + (purchase.freight or 0.0),
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
            selectinload(models.Purchase.items).selectinload(models.PurchaseItem.ingredient),
            selectinload(models.Purchase.supplier_entity),
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

    supplier_name = data.supplier
    supplier_id = None
    if data.supplier_id is not None:
        supplier_result = await db.execute(
            select(models.Supplier).where(
                models.Supplier.id == data.supplier_id,
                models.Supplier.user_id == current_user.id,
            )
        )
        supplier = supplier_result.scalar_one_or_none()
        if not supplier:
            raise HTTPException(404, "Fornecedor não encontrado")
        supplier_id = supplier.id
        supplier_name = supplier.name  # fallback exibido se o fornecedor for excluído depois (supplier_id vira NULL)

    purchase = models.Purchase(
        user_id=current_user.id,
        date=data.date,
        supplier=supplier_name,
        supplier_id=supplier_id,
        location=data.location,
        notes=data.notes,
        tax=data.tax or 0.0,
        freight=data.freight or 0.0,
    )
    db.add(purchase)
    await db.flush()

    # Imposto e frete são diluídos no custo de cada item, proporcionalmente
    # ao valor de cada um dentro da compra (rateio por valor).
    subtotal = sum(i.total_price for i in data.items)
    extra_pool = (data.tax or 0.0) + (data.freight or 0.0)

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

        ratio = (item_data.total_price / subtotal) if subtotal > 0 else (1 / len(data.items))
        allocated_extra = ratio * extra_pool
        effective_price = item_data.total_price + allocated_extra

        qty_base = convert_to_base(item_data.quantity, item_data.unit, ingredient.unit)
        unit_cost = effective_price / qty_base
        previous_unit_cost = ingredient.unit_cost

        item = models.PurchaseItem(
            purchase_id=purchase.id,
            ingredient_id=item_data.ingredient_id,
            quantity=item_data.quantity,
            unit=item_data.unit,
            total_price=item_data.total_price,
            allocated_extra=allocated_extra,
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
            stock.quantity += qty_base
            stock.updated_at = datetime.utcnow()
        else:
            stock = models.Stock(
                user_id=current_user.id,
                ingredient_id=item_data.ingredient_id,
                quantity=qty_base,
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
            selectinload(models.Purchase.items).selectinload(models.PurchaseItem.ingredient),
            selectinload(models.Purchase.supplier_entity),
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
            selectinload(models.PurchaseItem.purchase).selectinload(models.Purchase.supplier_entity),
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
            allocated_extra=i.allocated_extra,
            unit_cost=i.unit_cost,
            previous_unit_cost=i.previous_unit_cost,
            notes=i.notes,
            purchase_date=i.purchase.date,
            supplier=i.purchase.supplier_entity.name if i.purchase.supplier_entity else i.purchase.supplier,
            supplier_id=i.purchase.supplier_id,
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
            selectinload(models.Purchase.items).selectinload(models.PurchaseItem.ingredient),
            selectinload(models.Purchase.supplier_entity),
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
