from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Food(Base):
    __tablename__ = "foods"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    ingredients: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    category: Mapped[str] = mapped_column(String(80), index=True)
    price: Mapped[int]  # in Toman (integer: no floating-point money bugs)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))

    restaurant = relationship("Restaurant", back_populates="foods")
    reviews = relationship("Review", back_populates="food")