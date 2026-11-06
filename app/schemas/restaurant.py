from pydantic import BaseModel, ConfigDict, Field


class RestaurantBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    address: str = Field(min_length=2, max_length=300)
    latitude: float = Field(default=0.0, ge=-90, le=90)
    longitude: float = Field(default=0.0, ge=-180, le=180)
    avg_prep_time_minutes: int = Field(default=15, ge=1, le=240)


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantRead(RestaurantBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rating: float