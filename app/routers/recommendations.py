from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUser, DbSession
from app.models import User, UserRole
from app.schemas.recommendation import RecommendationRead
from app.services.recommendation_service import get_recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/{user_id}", response_model=RecommendationRead)
def recommend_foods(
    user_id: int,
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=10, ge=1, le=100),
):
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view recommendations for your own account",
        )
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    strategy, recommendations = get_recommendations(db, user_id, limit=limit)
    return RecommendationRead(
        user_id=user_id,
        strategy=strategy,
        recommendations=recommendations,
    )
