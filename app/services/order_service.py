from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Food, Order, OrderItem, OrderStatus, User, UserRole
from app.schemas.order import OrderCreate
from app.services.catalog_service import get_restaurant
from app.services.order_state import ensure_transition

MAX_QUANTITY_PER_ITEM = 50


class OrderNotFoundError(Exception):
    """Order does not exist or is not visible to this user."""


class OrderPermissionError(Exception):
    """User is not allowed to perform this status change."""


class InvalidOrderError(Exception):
    """The order content is invalid (unknown/unavailable food, ...)."""


def calculate_total(lines: Iterable[tuple[int, int]]) -> int:
    """lines: (unit_price, quantity) pairs. Returns the total in Toman."""
    return sum(unit_price * quantity for unit_price, quantity in lines)


def create_order(db: Session, customer: User, data: OrderCreate) -> Order:
    restaurant = get_restaurant(db, data.restaurant_id)  # raises if missing

    # Merge duplicate lines of the same food.
    quantities: dict[int, int] = defaultdict(int)
    for item in data.items:
        quantities[item.food_id] += item.quantity

    foods = {
        food.id: food
        for food in db.scalars(select(Food).where(Food.id.in_(list(quantities))))
    }

    missing = sorted(set(quantities) - set(foods))
    if missing:
        raise InvalidOrderError(f"Unknown food ids: {missing}")

    for food_id, quantity in quantities.items():
        food = foods[food_id]
        if food.restaurant_id != restaurant.id:
            raise InvalidOrderError(
                f"Food {food.id} does not belong to restaurant {restaurant.id}"
            )
        if not food.is_available:
            raise InvalidOrderError(f"Food '{food.name}' is not available")
        if quantity > MAX_QUANTITY_PER_ITEM:
            raise InvalidOrderError(
                f"At most {MAX_QUANTITY_PER_ITEM} of each food per order"
            )

    order = Order(
        customer_id=customer.id,
        restaurant_id=restaurant.id,
        status=OrderStatus.PENDING,
    )
    order.items = [
        OrderItem(food_id=food_id, quantity=quantity, unit_price=foods[food_id].price)
        for food_id, quantity in quantities.items()
    ]
    order.total_price = calculate_total(
        (item.unit_price, item.quantity) for item in order.items
    )

    db.add(order)  # order + items are saved in a single transaction
    db.commit()
    db.refresh(order)
    return order


def get_order(db: Session, order_id: int, user: User) -> Order:
    order = db.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    is_admin = user.role == UserRole.ADMIN
    if order is None or (not is_admin and order.customer_id != user.id):
        raise OrderNotFoundError(order_id)
    return order


def list_orders(
    db: Session,
    user: User,
    *,
    status: OrderStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Order]:
    stmt = select(Order).options(selectinload(Order.items))
    if user.role != UserRole.ADMIN:
        stmt = stmt.where(Order.customer_id == user.id)
    if status is not None:
        stmt = stmt.where(Order.status == status)
    stmt = stmt.order_by(Order.created_at.desc(), Order.id.desc())
    return list(db.scalars(stmt.offset(skip).limit(limit)))


def change_status(
    db: Session, order_id: int, user: User, new_status: OrderStatus
) -> Order:
    order = get_order(db, order_id, user)  # visibility check

    # Customers may only cancel their own orders; admins run the kitchen flow.
    if user.role != UserRole.ADMIN and new_status != OrderStatus.CANCELLED:
        raise OrderPermissionError()

    ensure_transition(order.status, new_status)  # raises InvalidStatusTransitionError

    order.status = new_status
    db.commit()
    db.refresh(order)
    return order