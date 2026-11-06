from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Food, Restaurant
from app.schemas.food import FoodCreate
from app.schemas.restaurant import RestaurantCreate


class RestaurantNotFoundError(Exception):
    """Restaurant id does not exist."""


class FoodNotFoundError(Exception):
    """Food id does not exist."""


class InvalidPriceRangeError(Exception):
    """min_price is greater than max_price."""


# ---------- Restaurants ----------

def list_restaurants(
    db: Session, *, search: str | None = None, skip: int = 0, limit: int = 20
) -> list[Restaurant]:
    stmt = select(Restaurant).order_by(Restaurant.rating.desc(), Restaurant.id)
    if search:
        stmt = stmt.where(Restaurant.name.icontains(search, autoescape=True))
    return list(db.scalars(stmt.offset(skip).limit(limit)))


def get_restaurant(db: Session, restaurant_id: int) -> Restaurant:
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise RestaurantNotFoundError(restaurant_id)
    return restaurant


def create_restaurant(db: Session, data: RestaurantCreate) -> Restaurant:
    restaurant = Restaurant(**data.model_dump())
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


# ---------- Foods ----------

def list_menu(
    db: Session, restaurant_id: int, *, only_available: bool = True
) -> list[Food]:
    get_restaurant(db, restaurant_id)  # raises if missing
    stmt = select(Food).where(Food.restaurant_id == restaurant_id)
    if only_available:
        stmt = stmt.where(Food.is_available.is_(True))
    return list(db.scalars(stmt.order_by(Food.category, Food.id)))


def search_foods(
    db: Session,
    *,
    q: str | None = None,
    category: str | None = None,
    restaurant_id: int | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    only_available: bool = True,
    skip: int = 0,
    limit: int = 20,
) -> list[Food]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise InvalidPriceRangeError()

    stmt = select(Food)
    if only_available:
        stmt = stmt.where(Food.is_available.is_(True))
    if q:
        stmt = stmt.where(
            or_(
                Food.name.icontains(q, autoescape=True),
                Food.description.icontains(q, autoescape=True),
                Food.ingredients.icontains(q, autoescape=True),
            )
        )
    if category:
        stmt = stmt.where(Food.category == category)
    if restaurant_id is not None:
        stmt = stmt.where(Food.restaurant_id == restaurant_id)
    if min_price is not None:
        stmt = stmt.where(Food.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Food.price <= max_price)

    return list(db.scalars(stmt.order_by(Food.id).offset(skip).limit(limit)))


def get_food(db: Session, food_id: int) -> Food:
    food = db.get(Food, food_id)
    if food is None:
        raise FoodNotFoundError(food_id)
    return food


def create_food(db: Session, data: FoodCreate) -> Food:
    get_restaurant(db, data.restaurant_id)  # raises if missing
    food = Food(**data.model_dump())
    db.add(food)
    db.commit()
    db.refresh(food)
    return food