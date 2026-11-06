from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Food, Order, OrderItem, OrderStatus, Restaurant, Review, User
from app.schemas.review import ReviewCreate
from app.services.catalog_service import get_food


class ReviewNotAllowedError(Exception):
    """The user has no delivered order containing this food."""


class DuplicateReviewError(Exception):
    """The user already reviewed this food."""


def has_delivered_order_with_food(db: Session, user_id: int, food_id: int) -> bool:
    stmt = (
        select(OrderItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.customer_id == user_id,
            Order.status == OrderStatus.DELIVERED,
            OrderItem.food_id == food_id,
        )
        .limit(1)
    )
    return db.scalar(stmt) is not None


def update_restaurant_rating(db: Session, restaurant_id: int) -> float | None:
    """Set the restaurant rating to the average of all its foods' review ratings."""
    average = db.scalar(
        select(func.avg(Review.rating))
        .select_from(Review)
        .join(Food, Food.id == Review.food_id)
        .where(Food.restaurant_id == restaurant_id)
    )
    if average is None:
        return None  # no reviews yet: keep the current rating
    restaurant = db.get(Restaurant, restaurant_id)
    restaurant.rating = round(float(average), 2)
    return restaurant.rating


def create_review(db: Session, user: User, data: ReviewCreate) -> Review:
    food = get_food(db, data.food_id)  # raises FoodNotFoundError

    if not has_delivered_order_with_food(db, user.id, food.id):
        raise ReviewNotAllowedError()

    already_reviewed = db.scalar(
        select(Review.id).where(Review.user_id == user.id, Review.food_id == food.id)
    )
    if already_reviewed is not None:
        raise DuplicateReviewError()

    review = Review(
        user_id=user.id,
        food_id=food.id,
        rating=data.rating,
        text=data.text.strip(),
    )
    db.add(review)
    db.flush()  # make the new review visible to the average query below
    update_restaurant_rating(db, food.restaurant_id)
    db.commit()  # review + restaurant rating are saved together
    db.refresh(review)
    return review


def list_food_reviews(
    db: Session, food_id: int, *, skip: int = 0, limit: int = 20
) -> list[Review]:
    get_food(db, food_id)  # raises FoodNotFoundError
    stmt = (
        select(Review)
        .options(selectinload(Review.analysis))
        .where(Review.food_id == food_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(stmt))