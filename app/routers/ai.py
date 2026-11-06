from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.review import ReviewAnalysisRead, ReviewAnalysisRequest
from app.services.review_ai_service import (
    ReviewAccessDeniedError,
    ReviewAIConfigurationError,
    ReviewAIInvalidOutputError,
    ReviewAIProviderError,
    ReviewNotFoundError,
    ReviewTextRequiredError,
    analyze_review,
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/analyze-review", response_model=ReviewAnalysisRead)
def analyze_customer_review(
    data: ReviewAnalysisRequest, db: DbSession, current_user: CurrentUser
):
    try:
        return analyze_review(db, data.review_id, current_user)
    except ReviewNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")
    except ReviewAccessDeniedError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "You can only analyze your own reviews",
        )
    except ReviewTextRequiredError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Review text is empty")
    except ReviewAIConfigurationError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Review analysis is not configured",
        )
    except ReviewAIProviderError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Review analysis provider is unavailable",
        )
    except ReviewAIInvalidOutputError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Review analysis provider returned an invalid response",
        )
