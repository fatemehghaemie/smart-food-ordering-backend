from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.food import FoodRead


RecommendationStrategy = Literal["personalized", "popular", "empty"]


class FoodRecommendation(BaseModel):
    food: FoodRead
    score: float = Field(ge=0, le=1)


class RecommendationRead(BaseModel):
    user_id: int
    strategy: RecommendationStrategy
    recommendations: list[FoodRecommendation]
