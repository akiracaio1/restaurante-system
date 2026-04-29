from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import models
import schemas

router = APIRouter()


def build_response(recipe: models.Recipe) -> schemas.RecipeResponse:
    total_cost = 0.0
    ingredients_resp = []
    for ri in recipe.recipe_ingredients:
        subtotal = ri.ingredient.unit_cost * ri.quantity
        total_cost += subtotal
        ingredients_resp.append(
            schemas.RecipeIngredientResponse(
                id=ri.id,
                ingredient_id=ri.ingredient_id,
                ingredient_name=ri.ingredient.name,
                ingredient_unit=ri.ingredient.unit,
                ingredient_unit_cost=ri.ingredient.unit_cost,
                quantity=ri.quantity,
                subtotal=round(subtotal, 4),
            )
        )
    cmv = (total_cost / recipe.sale_price * 100) if recipe.sale_price > 0 else 0.0
    return schemas.RecipeResponse(
        id=recipe.id,
        name=recipe.name,
        description=recipe.description,
        category=recipe.category,
        sale_price=recipe.sale_price,
        yield_portions=recipe.yield_portions,
        ingredients=ingredients_resp,
        total_cost=round(total_cost, 4),
        cmv_percent=round(cmv, 2),
    )


@router.get("/", response_model=List[schemas.RecipeResponse])
def list_recipes(db: Session = Depends(get_db)):
    recipes = db.query(models.Recipe).order_by(models.Recipe.name).all()
    return [build_response(r) for r in recipes]


@router.post("/", response_model=schemas.RecipeResponse, status_code=201)
def create_recipe(data: schemas.RecipeCreate, db: Session = Depends(get_db)):
    if db.query(models.Recipe).filter(models.Recipe.name == data.name).first():
        raise HTTPException(400, "Receita com este nome já existe")
    recipe = models.Recipe(**data.model_dump(exclude={"ingredients"}))
    db.add(recipe)
    db.flush()
    for ing in data.ingredients:
        if not db.query(models.Ingredient).filter(models.Ingredient.id == ing.ingredient_id).first():
            raise HTTPException(404, f"Ingrediente ID {ing.ingredient_id} não encontrado")
        db.add(
            models.RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ing.ingredient_id,
                quantity=ing.quantity,
            )
        )
    db.commit()
    db.refresh(recipe)
    return build_response(recipe)


@router.get("/{recipe_id}", response_model=schemas.RecipeResponse)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, "Receita não encontrada")
    return build_response(recipe)


@router.put("/{recipe_id}", response_model=schemas.RecipeResponse)
def update_recipe(
    recipe_id: int, data: schemas.RecipeUpdate, db: Session = Depends(get_db)
):
    recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, "Receita não encontrada")
    dup = db.query(models.Recipe).filter(
        models.Recipe.name == data.name, models.Recipe.id != recipe_id
    ).first()
    if dup:
        raise HTTPException(400, "Receita com este nome já existe")
    for k, v in data.model_dump(exclude={"ingredients"}).items():
        setattr(recipe, k, v)
    db.query(models.RecipeIngredient).filter(
        models.RecipeIngredient.recipe_id == recipe_id
    ).delete()
    for ing in data.ingredients:
        if not db.query(models.Ingredient).filter(models.Ingredient.id == ing.ingredient_id).first():
            raise HTTPException(404, f"Ingrediente ID {ing.ingredient_id} não encontrado")
        db.add(
            models.RecipeIngredient(
                recipe_id=recipe_id,
                ingredient_id=ing.ingredient_id,
                quantity=ing.quantity,
            )
        )
    db.commit()
    db.refresh(recipe)
    return build_response(recipe)


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, "Receita não encontrada")
    db.delete(recipe)
    db.commit()
