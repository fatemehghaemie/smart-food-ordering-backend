from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, DbSession
from app.pagination import Limit, Skip
from app.schemas.review import ReviewCreate, ReviewRead
from app.services import review_service
from app.services.catalog_service import FoodNotFoundError
from app.services.review_service import DuplicateReviewError, ReviewNotAllowedError

router = APIRouter(tags=["reviews"])


@router.post("/reviews", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
def create_review(data: ReviewCreate, db: DbSession, current_user: CurrentUser):
    try:
        return review_service.create_review(db, current_user, data)
    except FoodNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Food not found")
    except ReviewNotAllowedError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You can only review foods from your delivered orders",
        )
    except DuplicateReviewError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "You have already reviewed this food"
        )


@router.get("/foods/{food_id}/reviews", response_model=list[ReviewRead])
def list_food_reviews(food_id: int, db: DbSession, skip: Skip = 0, limit: Limit = 20):
    try:
        return review_service.list_food_reviews(db, food_id, skip=skip, limit=limit)
    except FoodNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Food not found")