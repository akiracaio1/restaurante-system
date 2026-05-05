from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import date, datetime


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

class ReductionStage(BaseModel):
    name: str
    yield_percentage: float


class IngredientBase(BaseModel):
    name: str
    unit: str
    unit_cost: float
    min_stock: float = 0.0
    purchase_unit: Optional[str] = None
    purchase_quantity: Optional[float] = None
    purchase_cost: Optional[float] = None
    yield_percentage: float = 100.0
    reduction_stages: Optional[List[ReductionStage]] = None
    processing_cost_per_unit: Optional[float] = None
    processing_cost_per_batch: Optional[float] = None
    processing_batch_size: Optional[float] = None


class IngredientCreate(IngredientBase):
    pass


class IngredientUpdate(IngredientBase):
    pass


class IngredientResponse(IngredientBase):
    id: int
    real_unit_cost: float = 0.0
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


class SubRecipeInput(BaseModel):
    sub_recipe_id: int
    portions: float


class SubRecipeResponse(BaseModel):
    id: int
    sub_recipe_id: int
    sub_recipe_name: str
    portions: float
    cost_per_portion: float
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
    sub_recipes: List[SubRecipeResponse] = []
    total_cost: float = 0.0
    cmv_percent: float = 0.0
    model_config = {"from_attributes": True}


# ── Purchases ─────────────────────────────────────────────────────────────────

class PurchaseItemInput(BaseModel):
    ingredient_id: int
    quantity: float
    unit: str
    total_price: float
    notes: Optional[str] = None


class PurchaseCreate(BaseModel):
    date: date
    supplier: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    items: List[PurchaseItemInput] = []


class PurchaseItemResponse(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    quantity: float
    unit: str
    total_price: float
    unit_cost: float
    previous_unit_cost: Optional[float] = None
    notes: Optional[str] = None
    model_config = {"from_attributes": True}


class PurchaseItemHistoryResponse(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    quantity: float
    unit: str
    total_price: float
    unit_cost: float
    previous_unit_cost: Optional[float] = None
    notes: Optional[str] = None
    purchase_date: date
    supplier: Optional[str] = None
    location: Optional[str] = None
    model_config = {"from_attributes": True}


class PurchaseResponse(BaseModel):
    id: int
    date: date
    supplier: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    items: List[PurchaseItemResponse] = []
    total: float = 0.0
    model_config = {"from_attributes": True}


# ── Stock ─────────────────────────────────────────────────────────────────────

class StockResponse(BaseModel):
    id: Optional[int] = None
    ingredient_id: int
    ingredient_name: str
    unit: str
    quantity: float
    min_stock: float
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class StockAdjustInput(BaseModel):
    quantity: float
    notes: Optional[str] = None


class StockMovementResponse(BaseModel):
    id: int
    type: str
    quantity: float
    reason: str
    notes: Optional[str] = None
    created_at: datetime
    ingredient_name: str
    model_config = {"from_attributes": True}
