from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    address: Mapped[str] = mapped_column(String(300))
    rating: Mapped[float] = mapped_column(Float, default=0.0)

    # Used by the delivery-time model (step 8)
    latitude: Mapped[float] = mapped_column(Float, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, default=0.0)
    avg_prep_time_minutes: Mapped[int] = mapped_column(default=15)

    foods = relationship("Food", back_populates="restaurant")
    orders = relationship("Order", back_populates="restaurant")