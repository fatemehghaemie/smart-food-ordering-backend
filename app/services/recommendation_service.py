from collections import Counter

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Food, Order, OrderItem, OrderStatus
from app.schemas.recommendation import RecommendationStrategy

PRICE_FEATURE_WEIGHT = 0.2


def _food_features(foods: list[Food]) -> csr_matrix:
    """Build TF-IDF text features and a scaled numeric price feature."""
    descriptions = [
        " ".join(
            part.strip()
            for part in (food.name, food.category, food.description, food.ingredients)
            if part and part.strip()
        )
        for food in foods
    ]
    text_matrix = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b").fit_transform(
        descriptions
    )
    prices = np.asarray([[food.price] for food in foods], dtype=float)
    scaled_prices = MinMaxScaler().fit_transform(prices) * PRICE_FEATURE_WEIGHT
    return hstack([text_matrix, csr_matrix(scaled_prices)], format="csr")


def _ordered_food_ids(db: Session, user_id: int) -> set[int]:
    statement = (
        select(OrderItem.food_id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.customer_id == user_id)
        .distinct()
    )
    return set(db.scalars(statement))


def _delivered_food_counts(db: Session, user_id: int | None = None) -> Counter[int]:
    statement = (
        select(OrderItem.food_id, func.sum(OrderItem.quantity))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status == OrderStatus.DELIVERED)
    )
    if user_id is not None:
        statement = statement.where(Order.customer_id == user_id)
    statement = statement.group_by(OrderItem.food_id)
    return Counter({food_id: int(quantity) for food_id, quantity in db.execute(statement)})


def _popular_recommendations(
    candidates: list[Food], purchase_counts: Counter[int], limit: int
) -> tuple[RecommendationStrategy, list[dict]]:
    popular = [food for food in candidates if purchase_counts.get(food.id, 0) > 0]
    if not popular:
        return "empty", []

    popular.sort(key=lambda food: (-purchase_counts[food.id], food.id))
    max_count = purchase_counts[popular[0].id]
    return "popular", [
        {"food": food, "score": round(purchase_counts[food.id] / max_count, 6)}
        for food in popular[:limit]
    ]


def get_recommendations(
    db: Session, user_id: int, *, limit: int = 10
) -> tuple[RecommendationStrategy, list[dict]]:
    """Recommend available foods from delivered-order history.

    Past orders of any status are excluded from recommendations. Delivered orders
    alone form the user profile; users without that history get global popular
    foods, or an empty list if there is no delivered-order data at all.
    """
    ordered_ids = _ordered_food_ids(db, user_id)
    candidates = list(
        db.scalars(select(Food).where(Food.is_available.is_(True)).order_by(Food.id))
    )
    candidates = [food for food in candidates if food.id not in ordered_ids]
    if not candidates:
        return "empty", []

    user_counts = _delivered_food_counts(db, user_id)
    if not user_counts:
        return _popular_recommendations(candidates, _delivered_food_counts(db), limit)

    all_foods = list(db.scalars(select(Food).order_by(Food.id)))
    feature_matrix = _food_features(all_foods)
    food_indices = {food.id: index for index, food in enumerate(all_foods)}

    history_ids = [food_id for food_id in user_counts if food_id in food_indices]
    if not history_ids:
        return _popular_recommendations(candidates, _delivered_food_counts(db), limit)

    history_indices = [food_indices[food_id] for food_id in history_ids]
    weights = np.asarray([user_counts[food_id] for food_id in history_ids], dtype=float)
    profile = np.asarray(
        feature_matrix[history_indices].multiply(weights[:, None]).sum(axis=0)
    )
    candidate_indices = [food_indices[food.id] for food in candidates]
    scores = cosine_similarity(profile, feature_matrix[candidate_indices])[0]

    ranked = sorted(
        zip(candidates, scores, strict=True),
        key=lambda item: (-float(item[1]), item[0].id),
    )[:limit]
    return "personalized", [
        {"food": food, "score": round(float(score), 6)}
        for food, score in ranked
    ]
