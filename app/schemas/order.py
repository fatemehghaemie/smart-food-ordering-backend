from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.enums import OrderStatus


class OrderItemCreate(BaseModel):
    food_id: int
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    restaurant_id: int
    items: list[OrderItemCreate] = Field(min_length=1, max_length=50)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    food_id: int
    quantity: int
    unit_price: int  # price at the time the order was placed

    @computed_field
    @property
    def line_total(self) -> int:
        return self.unit_price * self.quantity


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    restaurant_id: int
    status: OrderStatus
    total_price: int
    estimated_delivery_minutes: int | None
    created_at: datetime
    items: list[OrderItemRead]