from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    food_id: Mapped[int] = mapped_column(ForeignKey("foods.id"), index=True)
    rating: Mapped[int]  # 1..5, validated in schema + service
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="reviews")
    food = relationship("Food", back_populates="reviews")
    analysis = relationship(
        "ReviewAnalysis", back_populates="review", uselist=False,
        cascade="all, delete-orphan",
    )


class ReviewAnalysis(Base):
    """Validated LLM output for a review (step 7). One row per review."""
    __tablename__ = "review_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(
        ForeignKey("reviews.id"), unique=True, index=True
    )
    sentiment: Mapped[str] = mapped_column(String(20))      # positive|negative|mixed|neutral
    food_quality: Mapped[str] = mapped_column(String(20))
    delivery: Mapped[str] = mapped_column(String(20))
    packaging: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(Text)

    review = relationship("Review", back_populates="analysis")