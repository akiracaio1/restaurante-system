from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import models
import schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.IngredientResponse])
def list_ingredients(db: Session = Depends(get_db)):
    return db.query(models.Ingredient).order_by(models.Ingredient.name).all()


@router.post("/", response_model=schemas.IngredientResponse, status_code=201)
def create_ingredient(data: schemas.IngredientCreate, db: Session = Depends(get_db)):
    if db.query(models.Ingredient).filter(models.Ingredient.name == data.name).first():
        raise HTTPException(400, "Ingrediente com este nome já existe")
    obj = models.Ingredient(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{ingredient_id}", response_model=schemas.IngredientResponse)
def get_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    obj = db.query(models.Ingredient).filter(models.Ingredient.id == ingredient_id).first()
    if not obj:
        raise HTTPException(404, "Ingrediente não encontrado")
    return obj


@router.put("/{ingredient_id}", response_model=schemas.IngredientResponse)
def update_ingredient(
    ingredient_id: int, data: schemas.IngredientUpdate, db: Session = Depends(get_db)
):
    obj = db.query(models.Ingredient).filter(models.Ingredient.id == ingredient_id).first()
    if not obj:
        raise HTTPException(404, "Ingrediente não encontrado")
    dup = db.query(models.Ingredient).filter(
        models.Ingredient.name == data.name, models.Ingredient.id != ingredient_id
    ).first()
    if dup:
        raise HTTPException(400, "Ingrediente com este nome já existe")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{ingredient_id}", status_code=204)
def delete_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    obj = db.query(models.Ingredient).filter(models.Ingredient.id == ingredient_id).first()
    if not obj:
        raise HTTPException(404, "Ingrediente não encontrado")
    in_use = db.query(models.RecipeIngredient).filter(
        models.RecipeIngredient.ingredient_id == ingredient_id
    ).first()
    if in_use:
        raise HTTPException(400, "Ingrediente está sendo usado em uma ou mais receitas")
    db.delete(obj)
    db.commit()
