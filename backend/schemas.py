from pydantic import BaseModel, EmailStr
from typing import List, Optional


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Ingredients ───────────────────────────────────────────────────────────────

class IngredientBase(BaseModel):
    name: str
    unit: str
    unit_cost: float
    min_stock: float = 0.0


class IngredientCreate(IngredientBase):
    pass


class IngredientUpdate(IngredientBase):
    pass


class IngredientResponse(IngredientBase):
    id: int
    model_config = {"from_attributes": True}


# ── Recipes ───────────────────────────────────────────────────────────────────

class RecipeIngredientInput(BaseModel):
    ingredient_id: int
    quantity: float


class RecipeIngredientResponse(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    ingredient_unit: str
    ingredient_unit_cost: float
    quantity: float
    subtotal: float
    model_config = {"from_attributes": True}


class RecipeBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    sale_price: float
    yield_portions: int = 1


class RecipeCreate(RecipeBase):
    ingredients: List[RecipeIngredientInput] = []


class RecipeUpdate(RecipeBase):
    ingredients: List[RecipeIngredientInput] = []


class RecipeResponse(RecipeBase):
    id: int
    ingredients: List[RecipeIngredientResponse] = []
    total_cost: float = 0.0
    cmv_percent: float = 0.0
    model_config = {"from_attributes": True}
