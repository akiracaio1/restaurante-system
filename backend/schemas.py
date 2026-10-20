from pydantic import BaseModel, EmailStr, Field
from typing import List, Literal, Optional
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
    role: Optional[str] = None


class MeResponse(BaseModel):
    id: int
    email: str
    role: str


# ── Usuários (administração, somente Master) ─────────────────────────────────

class UserAdminCreate(BaseModel):
    email: EmailStr
    password: str
    role: str


class UserAdminUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserAdminResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    model_config = {"from_attributes": True}


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


class IngredientMergeInput(BaseModel):
    source_id: int  # o duplicado que será removido
    dry_run: bool = False


class IngredientMergeResponse(BaseModel):
    dry_run: bool
    target_id: int
    target_name: str
    source_id: int
    source_name: str
    unit: str
    recipes_moved: List[str] = []
    recipes_combined: List[str] = []  # receitas que usavam os dois: quantidades somadas
    channel_prices_updated: int = 0
    purchase_items_moved: int = 0
    movements_moved: int = 0
    stock_target_before: float = 0.0
    stock_source_before: float = 0.0
    stock_after: float = 0.0
    base_recipes: List[str] = []  # receitas cujo ingrediente-base da calculadora mudou


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
    stock_unit: str = "porção"
    min_stock: float = Field(default=0.0, ge=0)
    is_proportional: bool = False
    proportion_base_ingredient_id: Optional[int] = None


class RecipeCreate(RecipeBase):
    ingredients: List[RecipeIngredientInput] = []


class RecipeUpdate(RecipeBase):
    ingredients: List[RecipeIngredientInput] = []


class CategoryBase(BaseModel):
    name: str


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: int
    model_config = {"from_attributes": True}


class SalesChannelBase(BaseModel):
    name: str
    fee_percent: Optional[float] = None
    fixed_cost: Optional[float] = None


class SalesChannelCreate(SalesChannelBase):
    pass


class SalesChannelUpdate(SalesChannelBase):
    pass


class SalesChannelResponse(SalesChannelBase):
    id: int
    model_config = {"from_attributes": True}


class ChannelExtraIngredientInput(BaseModel):
    ingredient_id: int
    quantity: float


class ChannelExtraIngredientResponse(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    ingredient_unit: str
    quantity: float
    subtotal: float
    model_config = {"from_attributes": True}


class RecipeChannelPriceInput(BaseModel):
    sale_price: float
    extra_ingredients: List[ChannelExtraIngredientInput] = []


class RecipeChannelPriceResponse(BaseModel):
    id: int
    channel_id: int
    channel_name: str
    fee_percent: Optional[float] = None
    fixed_cost: Optional[float] = None
    sale_price: float
    extra_ingredients: List[ChannelExtraIngredientResponse] = []
    extra_cost: float = 0.0
    total_cost: float = 0.0
    cmv_percent: float = 0.0
    model_config = {"from_attributes": True}


class RecipeResponse(RecipeBase):
    id: int
    ingredients: List[RecipeIngredientResponse] = []
    sub_recipes: List[SubRecipeResponse] = []
    channel_prices: List[RecipeChannelPriceResponse] = []
    total_cost: float = 0.0
    cmv_percent: float = 0.0
    proportion_base_ingredient_name: Optional[str] = None
    model_config = {"from_attributes": True}


class RecipeStockUnitInput(BaseModel):
    stock_unit: str


class RecipeMinStockInput(BaseModel):
    min_stock: float = Field(ge=0)


# ── Calculadora de proporção ─────────────────────────────────────────────────

class ProportionCalculateInput(BaseModel):
    base_quantity: float


class ProportionIngredientResult(BaseModel):
    ingredient_id: int
    ingredient_name: str
    unit: str
    base_quantity: float
    calculated_quantity: float
    model_config = {"from_attributes": True}


class ProportionCalculateResponse(BaseModel):
    recipe_id: int
    recipe_name: str
    base_ingredient_id: int
    base_ingredient_name: str
    base_ingredient_unit: str
    scale_factor: float
    base_yield: float
    calculated_yield: float
    yield_unit: str
    ingredients: List[ProportionIngredientResult] = []


# ── Visão do perfil Operação ──────────────────────────────────────────────────
# Estes modelos NÃO herdam de nenhum schema financeiro e não declaram nenhum
# campo de custo, preço, margem ou compra: o que não existe aqui não é enviado.

class IngredientOperacaoResponse(BaseModel):
    id: int
    name: str
    unit: str
    yield_percentage: float = 100.0
    reduction_stages: List[ReductionStage] = []


class RecipeIngredientOperacaoResponse(BaseModel):
    ingredient_id: int
    ingredient_name: str
    ingredient_unit: str
    quantity: float


class SubRecipeOperacaoResponse(BaseModel):
    id: int
    sub_recipe_id: int
    sub_recipe_name: str
    portions: float


class RecipeOperacaoResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category: str
    yield_portions: int = 1
    stock_unit: str = "porção"
    is_proportional: bool = False
    proportion_base_ingredient_id: Optional[int] = None
    proportion_base_ingredient_name: Optional[str] = None
    ingredients: List[RecipeIngredientOperacaoResponse] = []
    sub_recipes: List[SubRecipeOperacaoResponse] = []


# ── Suppliers ─────────────────────────────────────────────────────────────────

class SupplierBase(BaseModel):
    name: str
    cnpj: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    contact_name: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(SupplierBase):
    pass


class SupplierResponse(SupplierBase):
    id: int
    model_config = {"from_attributes": True}


class SupplierWithStatsResponse(SupplierResponse):
    purchase_count: int = 0
    total_spent: float = 0.0


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
    supplier_id: Optional[int] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    tax: float = 0.0
    freight: float = 0.0
    items: List[PurchaseItemInput] = []


class PurchaseItemResponse(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    quantity: float
    unit: str
    total_price: float
    allocated_extra: float = 0.0
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
    allocated_extra: float = 0.0
    unit_cost: float
    previous_unit_cost: Optional[float] = None
    notes: Optional[str] = None
    purchase_date: date
    supplier: Optional[str] = None
    supplier_id: Optional[int] = None
    location: Optional[str] = None
    model_config = {"from_attributes": True}


class PurchaseResponse(BaseModel):
    id: int
    date: date
    supplier: Optional[str] = None
    supplier_id: Optional[int] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    tax: float = 0.0
    freight: float = 0.0
    items: List[PurchaseItemResponse] = []
    subtotal: float = 0.0
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


class InventoryItemInput(BaseModel):
    type: Literal["ingrediente", "receita"]
    id: int
    quantity: float = Field(ge=0)


class InventoryInput(BaseModel):
    items: List[InventoryItemInput] = Field(min_length=1, max_length=2000)
    notes: Optional[str] = None


class InventoryChange(BaseModel):
    type: str
    id: int
    name: str
    unit: str
    before: float
    after: float


class InventoryResponse(BaseModel):
    updated: int
    unchanged: int
    changes: List[InventoryChange] = []


class StockMovementResponse(BaseModel):
    id: int
    type: str
    quantity: float
    reason: str
    notes: Optional[str] = None
    created_at: datetime
    ingredient_name: str
    model_config = {"from_attributes": True}


class RecipeStockResponse(BaseModel):
    id: Optional[int] = None
    recipe_id: int
    recipe_name: str
    unit: str
    quantity: float
    min_stock: float = 0.0
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class RecipeStockMovementResponse(BaseModel):
    id: int
    type: str
    quantity: float
    reason: str
    notes: Optional[str] = None
    created_at: datetime
    recipe_name: str
    model_config = {"from_attributes": True}
