import json
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, UniqueConstraint, JSON, Date, DateTime
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    ingredients = relationship("Ingredient", back_populates="owner", cascade="all, delete-orphan")
    recipes = relationship("Recipe", back_populates="owner", cascade="all, delete-orphan")
    purchases = relationship("Purchase", back_populates="owner", cascade="all, delete-orphan")


class Ingredient(Base):
    __tablename__ = "ingredients"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_ingredient_user_name"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    unit = Column(String(20), nullable=False)
    unit_cost = Column(Float, nullable=False)
    min_stock = Column(Float, nullable=False, default=0.0)

    purchase_unit = Column(String(50), nullable=True)
    purchase_quantity = Column(Float, nullable=True)
    purchase_cost = Column(Float, nullable=True)
    yield_percentage = Column(Float, nullable=False, default=100.0)
    reduction_stages = Column(JSON, nullable=True)

    processing_cost_per_unit = Column(Float, nullable=True)
    processing_cost_per_batch = Column(Float, nullable=True)
    processing_batch_size = Column(Float, nullable=True)

    owner = relationship("User", back_populates="ingredients")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")

    @property
    def yield_total(self) -> float:
        stages = self.reduction_stages
        if isinstance(stages, str):
            stages = json.loads(stages)
        if stages:
            result = 1.0
            for stage in stages:
                if isinstance(stage, str):
                    stage = json.loads(stage)
                result *= stage.get("yield_percentage", 100) / 100.0
            return result * 100.0
        yt = self.yield_percentage
        return yt if yt is not None else 100.0

    @property
    def real_unit_cost(self) -> float:
        yt = self.yield_total
        extra = 0.0
        if self.processing_cost_per_unit is not None:
            extra = self.processing_cost_per_unit
        elif (
            self.processing_cost_per_batch is not None
            and self.processing_batch_size is not None
            and self.processing_batch_size > 0
        ):
            extra = self.processing_cost_per_batch / self.processing_batch_size
        if yt > 0:
            return (self.unit_cost + extra) / (yt / 100.0)
        return self.unit_cost + extra


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_recipe_user_name"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False)
    sale_price = Column(Float, nullable=False)
    yield_portions = Column(Integer, nullable=False, default=1)

    owner = relationship("User", back_populates="recipes")
    recipe_ingredients = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan"
    )
    sub_recipes = relationship(
        "RecipeSubRecipe",
        foreign_keys="[RecipeSubRecipe.parent_recipe_id]",
        back_populates="parent_recipe",
        cascade="all, delete-orphan",
    )
    channel_prices = relationship(
        "RecipeChannelPrice", back_populates="recipe", cascade="all, delete-orphan"
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantity = Column(Float, nullable=False)

    recipe = relationship("Recipe", back_populates="recipe_ingredients")
    ingredient = relationship("Ingredient", back_populates="recipe_ingredients")


class RecipeSubRecipe(Base):
    __tablename__ = "recipe_sub_recipes"

    id = Column(Integer, primary_key=True, index=True)
    parent_recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    sub_recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    portions = Column(Float, nullable=False)

    parent_recipe = relationship("Recipe", foreign_keys="[RecipeSubRecipe.parent_recipe_id]", back_populates="sub_recipes")
    sub_recipe = relationship("Recipe", foreign_keys="[RecipeSubRecipe.sub_recipe_id]")


class SalesChannel(Base):
    __tablename__ = "sales_channels"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_channel_user_name"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    fee_percent = Column(Float, nullable=True)
    fixed_cost = Column(Float, nullable=True)

    owner = relationship("User")


class RecipeChannelPrice(Base):
    __tablename__ = "recipe_channel_prices"
    __table_args__ = (UniqueConstraint("recipe_id", "channel_id", name="uq_recipe_channel"),)

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_id = Column(Integer, ForeignKey("sales_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    sale_price = Column(Float, nullable=False)

    recipe = relationship("Recipe", back_populates="channel_prices")
    channel = relationship("SalesChannel")
    extra_ingredients = relationship(
        "RecipeChannelIngredient", back_populates="channel_price", cascade="all, delete-orphan"
    )


class RecipeChannelIngredient(Base):
    __tablename__ = "recipe_channel_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_channel_price_id = Column(Integer, ForeignKey("recipe_channel_prices.id", ondelete="CASCADE"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantity = Column(Float, nullable=False)

    channel_price = relationship("RecipeChannelPrice", back_populates="extra_ingredients")
    ingredient = relationship("Ingredient")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    supplier = Column(String(200), nullable=True)
    location = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="purchases")
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    total_price = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=False)
    previous_unit_cost = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    purchase = relationship("Purchase", back_populates="items")
    ingredient = relationship("Ingredient")
    stock_movements = relationship("StockMovement", back_populates="purchase_item")


class Stock(Base):
    __tablename__ = "stock"
    __table_args__ = (UniqueConstraint("user_id", "ingredient_id", name="uq_stock_user_ingredient"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantity = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")
    ingredient = relationship("Ingredient")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    type = Column(String(20), nullable=False)
    quantity = Column(Float, nullable=False)
    reason = Column(String(30), nullable=False)
    purchase_item_id = Column(Integer, ForeignKey("purchase_items.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")
    ingredient = relationship("Ingredient")
    purchase_item = relationship("PurchaseItem", back_populates="stock_movements")
