from pydantic import BaseModel, ConfigDict, Field


class FoodCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str = Field(default="", max_length=1000)
    ingredients: str = Field(default="", max_length=1000)  # comma-separated
    category: str = Field(min_length=2, max_length=80)
    price: int = Field(gt=0, description="Price in Toman")
    restaurant_id: int
    is_available: bool = True


class FoodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    ingredients: str
    category: str
    price: int
    is_available: bool
    restaurant_id: int