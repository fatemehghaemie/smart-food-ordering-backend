from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401  (registers all models)
from app.database import Base, engine
from app.routers import ai, auth, foods, orders, recommendations, restaurants, reviews


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Smart Food Ordering & Recommendation Backend",
    version="0.5.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(restaurants.router)
app.include_router(foods.router)
app.include_router(orders.router)
app.include_router(reviews.router)
app.include_router(recommendations.router)
app.include_router(ai.router)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}
