from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import DbSession, require_role
from app.models import UserRole
from app.pagination import Limit, Skip
from app.schemas.food import FoodCreate, FoodRead
from app.services import catalog_service
from app.services.catalog_service import (
    FoodNotFoundError,
    InvalidPriceRangeError,
    RestaurantNotFoundError,
)

router = APIRouter(prefix="/foods", tags=["foods"])


@router.get("", response_model=list[FoodRead])
def search_foods(
    db: DbSession,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    category: str | None = None,
    restaurant_id: int | None = None,
    min_price: Annotated[int | None, Query(ge=0)] = None,
    max_price: Annotated[int | None, Query(ge=0)] = None,
    only_available: bool = True,
    skip: Skip = 0,
    limit: Limit = 20,
):
    try:
        return catalog_service.search_foods(
            db,
            q=q,
            category=category,
            restaurant_id=restaurant_id,
            min_price=min_price,
            max_price=max_price,
            only_available=only_available,
            skip=skip,
            limit=limit,
        )
    except InvalidPriceRangeError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "min_price must be less than or equal to max_price",
        )


@router.get("/{food_id}", response_model=FoodRead)
def get_food(food_id: int, db: DbSession):
    try:
        return catalog_service.get_food(db, food_id)
    except FoodNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Food not found")


@router.post(
    "",
    response_model=FoodRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def create_food(data: FoodCreate, db: DbSession):
    try:
        return catalog_service.create_food(db, data)
    except RestaurantNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restaurant not found")