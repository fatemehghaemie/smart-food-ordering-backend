"""Load initial data: `python -m app.seed` (safe to run multiple times)."""
import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Food, Restaurant, User, UserRole
from app.security import hash_password

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _read_csv(filename: str) -> list[dict]:
    # utf-8-sig also handles files saved with a BOM (e.g. by Windows Notepad)
    with open(DATA_DIR / filename, encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def seed_restaurants(db: Session) -> dict[str, Restaurant]:
    existing = {r.name: r for r in db.scalars(select(Restaurant))}
    for row in _read_csv("restaurants.csv"):
        if row["name"] in existing:
            continue
        restaurant = Restaurant(
            name=row["name"],
            address=row["address"],
            rating=float(row["rating"]),
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            avg_prep_time_minutes=int(row["avg_prep_time_minutes"]),
        )
        db.add(restaurant)
        existing[restaurant.name] = restaurant
    db.flush()  # assigns ids
    return existing


def seed_foods(db: Session, restaurants: dict[str, Restaurant]) -> int:
    existing = {(f.restaurant_id, f.name) for f in db.scalars(select(Food))}
    added = 0
    for row in _read_csv("foods.csv"):
        restaurant = restaurants.get(row["restaurant"])
        if restaurant is None:
            raise ValueError(f"Unknown restaurant in foods.csv: {row['restaurant']}")
        if (restaurant.id, row["name"]) in existing:
            continue
        db.add(
            Food(
                name=row["name"],
                description=row["description"],
                ingredients=", ".join(row["ingredients"].split("|")),
                category=row["category"],
                price=int(row["price"]),
                restaurant_id=restaurant.id,
            )
        )
        added += 1
    return added


def seed_admin(db: Session) -> bool:
    if not settings.admin_email or not settings.admin_password:
        return False
    email = settings.admin_email.strip().lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        return False
    db.add(
        User(
            name="Admin",
            email=email,
            hashed_password=hash_password(settings.admin_password),
            role=UserRole.ADMIN,
        )
    )
    return True


def seed_all(db: Session) -> dict:
    restaurants = seed_restaurants(db)
    foods_added = seed_foods(db, restaurants)
    admin_created = seed_admin(db)
    db.commit()
    return {
        "restaurants_total": len(restaurants),
        "foods_added": foods_added,
        "admin_created": admin_created,
    }


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        print(seed_all(session))