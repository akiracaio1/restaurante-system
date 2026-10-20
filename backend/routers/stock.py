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
    ing_result = await db.execute(
        select(models.Ingredient)
        .where(models.Ingredient.user_id == current_user.account_id)
        .order_by(models.Ingredient.name)
    )
    ingredients = ing_result.scalars().all()

    stock_result = await db.execute(
        select(models.Stock)
        .where(models.Stock.user_id == current_user.account_id)
    )
    stock_by_ing = {s.ingredient_id: s for s in stock_result.scalars().all()}

    return [
        schemas.StockResponse(
            id=stock_by_ing[ing.id].id if ing.id in stock_by_ing else None,
            ingredient_id=ing.id,
            ingredient_name=ing.name,
            unit=ing.unit,
            quantity=stock_by_ing[ing.id].quantity if ing.id in stock_by_ing else 0.0,
            min_stock=ing.min_stock or 0.0,
            updated_at=stock_by_ing[ing.id].updated_at if ing.id in stock_by_ing else None,
        )
        for ing in ingredients
    ]


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
            models.StockMovement.user_id == current_user.account_id,
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
            models.Stock.user_id == current_user.account_id,
            models.Stock.ingredient_id == ingredient_id,
        )
    )
    stock = stock_result.scalar_one_or_none()

    if not stock:
        ing_result = await db.execute(
            select(models.Ingredient).where(
                models.Ingredient.id == ingredient_id,
                models.Ingredient.user_id == current_user.account_id,
            )
        )
        if not ing_result.scalar_one_or_none():
            raise HTTPException(404, "Ingrediente não encontrado")
        stock = models.Stock(
            user_id=current_user.account_id,
            ingredient_id=ingredient_id,
            quantity=data.quantity,
            updated_at=datetime.utcnow(),
        )
        db.add(stock)
    else:
        stock.quantity = data.quantity
        stock.updated_at = datetime.utcnow()

    movement = models.StockMovement(
        user_id=current_user.account_id,
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
            models.Stock.user_id == current_user.account_id,
            models.Stock.ingredient_id == ingredient_id,
        )
        .options(selectinload(models.Stock.ingredient))
    )
    return _to_response(result.scalar_one())


def _fmt_qty(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", ",") or "0"


@router.post("/inventario", response_model=schemas.InventoryResponse)
async def save_inventory(
    data: schemas.InventoryInput,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Contagem física: define a quantidade de vários itens de uma vez, tudo ou nada."""
    keys = [(i.type, i.id) for i in data.items]
    if len(set(keys)) != len(keys):
        raise HTTPException(400, "Há itens repetidos no inventário")

    ing_ids = [i.id for i in data.items if i.type == "ingrediente"]
    rec_ids = [i.id for i in data.items if i.type == "receita"]
    account = current_user.account_id

    ingredients, stocks, recipes, recipe_stocks = {}, {}, {}, {}
    if ing_ids:
        rows = await db.execute(
            select(models.Ingredient).where(models.Ingredient.id.in_(ing_ids), models.Ingredient.user_id == account)
        )
        ingredients = {r.id: r for r in rows.scalars().all()}
        rows = await db.execute(
            select(models.Stock).where(models.Stock.user_id == account, models.Stock.ingredient_id.in_(ing_ids))
        )
        stocks = {r.ingredient_id: r for r in rows.scalars().all()}
    if rec_ids:
        rows = await db.execute(
            select(models.Recipe).where(models.Recipe.id.in_(rec_ids), models.Recipe.user_id == account)
        )
        recipes = {r.id: r for r in rows.scalars().all()}
        rows = await db.execute(
            select(models.RecipeStock).where(models.RecipeStock.user_id == account, models.RecipeStock.recipe_id.in_(rec_ids))
        )
        recipe_stocks = {r.recipe_id: r for r in rows.scalars().all()}

    for i in ing_ids:
        if i not in ingredients:
            raise HTTPException(404, f"Ingrediente ID {i} não encontrado")
    for i in rec_ids:
        if i not in recipes:
            raise HTTPException(404, f"Receita ID {i} não encontrada")

    now = datetime.utcnow()
    changes: list[schemas.InventoryChange] = []
    unchanged = 0
    for item in data.items:
        is_ing = item.type == "ingrediente"
        current = (stocks if is_ing else recipe_stocks).get(item.id)
        before = current.quantity if current else 0.0
        if round(item.quantity, 6) == round(before, 6):
            unchanged += 1
            continue

        note = f"Inventário: {_fmt_qty(before)} → {_fmt_qty(item.quantity)}"
        if data.notes:
            note += f" · {data.notes}"
        if is_ing:
            if current:
                current.quantity, current.updated_at = item.quantity, now
            else:
                db.add(models.Stock(user_id=account, ingredient_id=item.id, quantity=item.quantity, updated_at=now))
            db.add(models.StockMovement(
                user_id=account, ingredient_id=item.id, type="ajuste",
                quantity=item.quantity, reason="inventario", notes=note,
            ))
            obj, unit = ingredients[item.id], ingredients[item.id].unit
        else:
            if current:
                current.quantity, current.updated_at = item.quantity, now
            else:
                db.add(models.RecipeStock(user_id=account, recipe_id=item.id, quantity=item.quantity, updated_at=now))
            db.add(models.RecipeStockMovement(
                user_id=account, recipe_id=item.id, type="ajuste",
                quantity=item.quantity, reason="inventario", notes=note,
            ))
            obj, unit = recipes[item.id], recipes[item.id].stock_unit or "porção"
        changes.append(schemas.InventoryChange(
            type=item.type, id=item.id, name=obj.name, unit=unit, before=before, after=item.quantity,
        ))

    await db.commit()
    return schemas.InventoryResponse(updated=len(changes), unchanged=unchanged, changes=changes)


def _to_recipe_response(stock: models.RecipeStock) -> schemas.RecipeStockResponse:
    return schemas.RecipeStockResponse(
        id=stock.id,
        recipe_id=stock.recipe_id,
        recipe_name=stock.recipe.name if stock.recipe else '',
        unit=stock.recipe.stock_unit if stock.recipe else 'porção',
        quantity=stock.quantity,
        min_stock=(stock.recipe.min_stock or 0.0) if stock.recipe else 0.0,
        updated_at=stock.updated_at,
    )


@router.get("/receitas/", response_model=List[schemas.RecipeStockResponse])
async def list_recipe_stock(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    recipe_result = await db.execute(
        select(models.Recipe)
        .where(models.Recipe.user_id == current_user.account_id)
        .order_by(models.Recipe.name)
    )
    recipes = recipe_result.scalars().all()

    stock_result = await db.execute(
        select(models.RecipeStock)
        .where(models.RecipeStock.user_id == current_user.account_id)
    )
    stock_by_recipe = {s.recipe_id: s for s in stock_result.scalars().all()}

    return [
        schemas.RecipeStockResponse(
            id=stock_by_recipe[r.id].id if r.id in stock_by_recipe else None,
            recipe_id=r.id,
            recipe_name=r.name,
            unit=r.stock_unit or 'porção',
            quantity=stock_by_recipe[r.id].quantity if r.id in stock_by_recipe else 0.0,
            min_stock=r.min_stock or 0.0,
            updated_at=stock_by_recipe[r.id].updated_at if r.id in stock_by_recipe else None,
        )
        for r in recipes
    ]


# /receitas/movimentacoes/ must be before /receitas/{recipe_id} to avoid routing conflicts
@router.get("/receitas/movimentacoes/{recipe_id}", response_model=List[schemas.RecipeStockMovementResponse])
async def list_recipe_movements(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.RecipeStockMovement)
        .where(
            models.RecipeStockMovement.user_id == current_user.account_id,
            models.RecipeStockMovement.recipe_id == recipe_id,
        )
        .options(selectinload(models.RecipeStockMovement.recipe))
        .order_by(models.RecipeStockMovement.created_at.desc())
    )
    movements = result.scalars().all()
    return [
        schemas.RecipeStockMovementResponse(
            id=m.id,
            type=m.type,
            quantity=m.quantity,
            reason=m.reason,
            notes=m.notes,
            created_at=m.created_at,
            recipe_name=m.recipe.name if m.recipe else '',
        )
        for m in movements
    ]


@router.put("/receitas/{recipe_id}", response_model=schemas.RecipeStockResponse)
async def adjust_recipe_stock(
    recipe_id: int,
    data: schemas.StockAdjustInput,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    stock_result = await db.execute(
        select(models.RecipeStock)
        .where(
            models.RecipeStock.user_id == current_user.account_id,
            models.RecipeStock.recipe_id == recipe_id,
        )
    )
    stock = stock_result.scalar_one_or_none()

    if not stock:
        recipe_result = await db.execute(
            select(models.Recipe).where(
                models.Recipe.id == recipe_id,
                models.Recipe.user_id == current_user.account_id,
            )
        )
        if not recipe_result.scalar_one_or_none():
            raise HTTPException(404, "Receita não encontrada")
        stock = models.RecipeStock(
            user_id=current_user.account_id,
            recipe_id=recipe_id,
            quantity=data.quantity,
            updated_at=datetime.utcnow(),
        )
        db.add(stock)
    else:
        stock.quantity = data.quantity
        stock.updated_at = datetime.utcnow()

    movement = models.RecipeStockMovement(
        user_id=current_user.account_id,
        recipe_id=recipe_id,
        type='ajuste',
        quantity=data.quantity,
        reason='ajuste_manual',
        notes=data.notes,
    )
    db.add(movement)
    await db.commit()

    result = await db.execute(
        select(models.RecipeStock)
        .where(
            models.RecipeStock.user_id == current_user.account_id,
            models.RecipeStock.recipe_id == recipe_id,
        )
        .options(selectinload(models.RecipeStock.recipe))
    )
    return _to_recipe_response(result.scalar_one())
