from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List

from database import get_db
from auth import get_current_user
from routers.purchases import _to_response as purchase_to_response
import models
import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.SupplierWithStatsResponse])
async def list_suppliers(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Supplier)
        .where(models.Supplier.user_id == current_user.id)
        .order_by(models.Supplier.name)
    )
    suppliers = result.scalars().all()

    stats_result = await db.execute(
        select(
            models.Purchase.supplier_id,
            func.count(models.Purchase.id),
            func.sum(models.PurchaseItem.total_price),
        )
        .join(models.PurchaseItem, models.PurchaseItem.purchase_id == models.Purchase.id)
        .where(
            models.Purchase.user_id == current_user.id,
            models.Purchase.supplier_id.isnot(None),
        )
        .group_by(models.Purchase.supplier_id)
    )
    # count distinct purchases per supplier (not items) separately, since the
    # join above multiplies purchase rows by item count
    count_result = await db.execute(
        select(models.Purchase.supplier_id, func.count(func.distinct(models.Purchase.id)))
        .where(
            models.Purchase.user_id == current_user.id,
            models.Purchase.supplier_id.isnot(None),
        )
        .group_by(models.Purchase.supplier_id)
    )
    counts = {row[0]: row[1] for row in count_result.all()}
    totals: dict[int, float] = {}
    for supplier_id, _count, total in stats_result.all():
        totals[supplier_id] = (totals.get(supplier_id, 0.0)) + (total or 0.0)

    return [
        schemas.SupplierWithStatsResponse(
            id=s.id,
            name=s.name,
            cnpj=s.cnpj,
            phone=s.phone,
            email=s.email,
            contact_name=s.contact_name,
            address=s.address,
            notes=s.notes,
            purchase_count=counts.get(s.id, 0),
            total_spent=round(totals.get(s.id, 0.0), 2),
        )
        for s in suppliers
    ]


@router.post("/", response_model=schemas.SupplierResponse, status_code=201)
async def create_supplier(
    data: schemas.SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    dup = await db.execute(
        select(models.Supplier).where(
            models.Supplier.user_id == current_user.id,
            models.Supplier.name == data.name,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(400, "Fornecedor com este nome já existe")
    obj = models.Supplier(**data.model_dump(), user_id=current_user.id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{supplier_id}", response_model=schemas.SupplierResponse)
async def get_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Supplier).where(
            models.Supplier.id == supplier_id,
            models.Supplier.user_id == current_user.id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Fornecedor não encontrado")
    return obj


@router.put("/{supplier_id}", response_model=schemas.SupplierResponse)
async def update_supplier(
    supplier_id: int,
    data: schemas.SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Supplier).where(
            models.Supplier.id == supplier_id,
            models.Supplier.user_id == current_user.id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Fornecedor não encontrado")

    dup = await db.execute(
        select(models.Supplier).where(
            models.Supplier.user_id == current_user.id,
            models.Supplier.name == data.name,
            models.Supplier.id != supplier_id,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(400, "Fornecedor com este nome já existe")

    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Supplier).where(
            models.Supplier.id == supplier_id,
            models.Supplier.user_id == current_user.id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Fornecedor não encontrado")
    await db.delete(obj)
    await db.commit()


@router.get("/{supplier_id}/compras", response_model=List[schemas.PurchaseResponse])
async def supplier_purchases(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    supplier_check = await db.execute(
        select(models.Supplier).where(
            models.Supplier.id == supplier_id,
            models.Supplier.user_id == current_user.id,
        )
    )
    if not supplier_check.scalar_one_or_none():
        raise HTTPException(404, "Fornecedor não encontrado")

    result = await db.execute(
        select(models.Purchase)
        .where(
            models.Purchase.user_id == current_user.id,
            models.Purchase.supplier_id == supplier_id,
        )
        .options(
            selectinload(models.Purchase.items).selectinload(models.PurchaseItem.ingredient),
            selectinload(models.Purchase.supplier_entity),
        )
        .order_by(models.Purchase.date.desc())
    )
    return [purchase_to_response(p) for p in result.scalars().all()]
