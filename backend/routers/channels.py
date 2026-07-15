from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database import get_db
from auth import get_current_user
import models
import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.SalesChannelResponse])
async def list_channels(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.SalesChannel)
        .where(models.SalesChannel.user_id == current_user.id)
        .order_by(models.SalesChannel.name)
    )
    return result.scalars().all()


@router.post("/", response_model=schemas.SalesChannelResponse, status_code=201)
async def create_channel(
    data: schemas.SalesChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    dup = await db.execute(
        select(models.SalesChannel).where(
            models.SalesChannel.user_id == current_user.id,
            models.SalesChannel.name == data.name,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(400, "Canal de venda com este nome já existe")
    obj = models.SalesChannel(**data.model_dump(), user_id=current_user.id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.put("/{channel_id}", response_model=schemas.SalesChannelResponse)
async def update_channel(
    channel_id: int,
    data: schemas.SalesChannelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.SalesChannel).where(
            models.SalesChannel.id == channel_id,
            models.SalesChannel.user_id == current_user.id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Canal de venda não encontrado")
    dup = await db.execute(
        select(models.SalesChannel).where(
            models.SalesChannel.user_id == current_user.id,
            models.SalesChannel.name == data.name,
            models.SalesChannel.id != channel_id,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(400, "Canal de venda com este nome já existe")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.SalesChannel).where(
            models.SalesChannel.id == channel_id,
            models.SalesChannel.user_id == current_user.id,
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Canal de venda não encontrado")
    await db.delete(obj)
    await db.commit()
