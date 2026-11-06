from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUser, DbSession
from app.models import OrderStatus
from app.pagination import Limit, Skip
from app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate
from app.services import order_service
from app.services.catalog_service import RestaurantNotFoundError
from app.services.order_service import (
    InvalidOrderError,
    OrderNotFoundError,
    OrderPermissionError,
)
from app.services.order_state import InvalidStatusTransitionError

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate, db: DbSession, current_user: CurrentUser):
    try:
        return order_service.create_order(db, current_user, data)
    except RestaurantNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restaurant not found")
    except InvalidOrderError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))


@router.get("", response_model=list[OrderRead])
def list_orders(
    db: DbSession,
    current_user: CurrentUser,
    status_filter: Annotated[OrderStatus | None, Query(alias="status")] = None,
    skip: Skip = 0,
    limit: Limit = 20,
):
    """Customers see their own order history; admins see all orders."""
    return order_service.list_orders(
        db, current_user, status=status_filter, skip=skip, limit=limit
    )


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, db: DbSession, current_user: CurrentUser):
    try:
        return order_service.get_order(db, order_id, current_user)
    except OrderNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    try:
        return order_service.change_status(db, order_id, current_user, data.status)
    except OrderNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    except OrderPermissionError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Customers can only cancel their own orders",
        )
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))