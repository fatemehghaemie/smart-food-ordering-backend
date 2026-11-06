import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models import Review, ReviewAnalysis, User, UserRole
from app.schemas.review import AspectLabel, SentimentLabel

ANALYSIS_PROMPT = """تو یک تحلیل‌گر بازخورد مشتری برای سامانه سفارش غذا هستی.
نظر را فقط بر اساس متن داده‌شده تحلیل کن و برای موضوعی که ذکر نشده مقدار
not_mentioned بگذار. sentiment باید یکی از positive, negative, mixed, neutral
باشد. food_quality، delivery و packaging هر کدام باید یکی از positive, negative,
neutral, not_mentioned باشند. summary را کوتاه و به زبان فارسی بنویس.
فقط یک شیء JSON معتبر با کلیدهای sentiment، food_quality، delivery، packaging،
summary برگردان و هیچ متن دیگری ننویس."""


class ReviewAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentiment: SentimentLabel
    food_quality: AspectLabel
    delivery: AspectLabel
    packaging: AspectLabel
    summary: str = Field(min_length=1, max_length=500)

    @field_validator("summary")
    @classmethod
    def summary_must_not_be_blank(cls, value: str) -> str:
        summary = value.strip()
        if not summary:
            raise ValueError("summary must not be blank")
        return summary


class ReviewAIError(Exception):
    """Base class for safe, expected review-analysis failures."""


class ReviewNotFoundError(ReviewAIError):
    pass


class ReviewAccessDeniedError(ReviewAIError):
    pass


class ReviewTextRequiredError(ReviewAIError):
    pass


class ReviewAIConfigurationError(ReviewAIError):
    pass


class ReviewAIProviderError(ReviewAIError):
    pass


class ReviewAIInvalidOutputError(ReviewAIError):
    pass


def _request_completion(review_text: str) -> dict:
    if not settings.llm_api_key or not settings.llm_api_url or not settings.llm_model:
        raise ReviewAIConfigurationError("Review analysis is not configured")

    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                settings.llm_api_url,
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": ANALYSIS_PROMPT},
                        {"role": "user", "content": review_text},
                    ],
                },
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise ReviewAIProviderError("Review analysis provider request failed") from exc
    except ValueError as exc:
        raise ReviewAIInvalidOutputError("Provider returned invalid JSON") from exc


def _call_model(review_text: str) -> ReviewAnalysisOutput:
    payload = _request_completion(review_text)
    try:
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise TypeError("Model content must be a JSON string")
        return ReviewAnalysisOutput.model_validate_json(content)
    except (KeyError, IndexError, TypeError, ValidationError) as exc:
        raise ReviewAIInvalidOutputError("Model returned an invalid analysis") from exc


def analyze_review(db: Session, review_id: int, requester: User) -> ReviewAnalysis:
    review = db.scalar(
        select(Review)
        .options(selectinload(Review.analysis))
        .where(Review.id == review_id)
    )
    if review is None:
        raise ReviewNotFoundError()
    if requester.role != UserRole.ADMIN and review.user_id != requester.id:
        raise ReviewAccessDeniedError()
    if review.analysis is not None:
        return review.analysis
    if not review.text.strip():
        raise ReviewTextRequiredError()

    result = _call_model(review.text)
    analysis = ReviewAnalysis(review_id=review.id, **result.model_dump())
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis
