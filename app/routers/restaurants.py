from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import DbSession, require_role
from app.models import UserRole
from app.pagination import Limit, Skip
from app.schemas.food import FoodRead
from app.schemas.restaurant import RestaurantCreate, RestaurantRead
from app.services import catalog_service
from app.services.catalog_service import RestaurantNotFoundError

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("", response_model=list[RestaurantRead])
def list_restaurants(
    db: DbSession, search: str | None = None, skip: Skip = 0, limit: Limit = 20
):
    return catalog_service.list_restaurants(db, search=search, skip=skip, limit=limit)


@router.get("/{restaurant_id}", response_model=RestaurantRead)
def get_restaurant(restaurant_id: int, db: DbSession):
    try:
        return catalog_service.get_restaurant(db, restaurant_id)
    except RestaurantNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restaurant not found")


@router.get("/{restaurant_id}/menu", response_model=list[FoodRead])
def get_menu(restaurant_id: int, db: DbSession, only_available: bool = True):
    try:
        return catalog_service.list_menu(
            db, restaurant_id, only_available=only_available
        )
    except RestaurantNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Restaurant not found")


@router.post(
    "",
    response_model=RestaurantRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def create_restaurant(data: RestaurantCreate, db: DbSession):
    return catalog_service.create_restaurant(db, data)