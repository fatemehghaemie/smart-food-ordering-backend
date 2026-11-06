from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SentimentLabel = Literal["positive", "negative", "mixed", "neutral"]
AspectLabel = Literal["positive", "negative", "neutral", "not_mentioned"]


class ReviewCreate(BaseModel):
    food_id: int
    rating: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=2000)


class ReviewAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sentiment: SentimentLabel
    food_quality: AspectLabel
    delivery: AspectLabel
    packaging: AspectLabel
    summary: str = Field(min_length=1, max_length=500)


class ReviewAnalysisRequest(BaseModel):
    review_id: int = Field(gt=0)


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    food_id: int
    rating: int
    text: str
    created_at: datetime
    analysis: ReviewAnalysisRead | None = None  # filled by the LLM step later
