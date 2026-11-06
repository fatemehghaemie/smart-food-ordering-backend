from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401  (registers all models)
from app.database import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Smart Food Ordering & Recommendation Backend",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}