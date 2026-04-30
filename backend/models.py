from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    ingredients = relationship("Ingredient", back_populates="owner", cascade="all, delete-orphan")
    recipes = relationship("Recipe", back_populates="owner", cascade="all, delete-orphan")


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

    owner = relationship("User", back_populates="ingredients")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")

    @property
    def yield_total(self) -> float:
        stages = self.reduction_stages
        if stages:
            result = 1.0
            for stage in stages:
                result *= stage.get("yield_percentage", 100) / 100.0
            return result * 100.0
        yt = self.yield_percentage
        return yt if yt is not None else 100.0

    @property
    def real_unit_cost(self) -> float:
        yt = self.yield_total
        if yt > 0:
            return self.unit_cost / (yt / 100.0)
        return self.unit_cost


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


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantity = Column(Float, nullable=False)

    recipe = relationship("Recipe", back_populates="recipe_ingredients")
    ingredient = relationship("Ingredient", back_populates="recipe_ingredients")
