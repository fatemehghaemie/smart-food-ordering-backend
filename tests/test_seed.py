from sqlalchemy import func, select

from app.models import Food, Restaurant
from app.seed import seed_all


def test_seed_loads_expected_data(db_session):
    result = seed_all(db_session)
    assert result["restaurants_total"] == 5
    assert db_session.scalar(select(func.count()).select_from(Food)) == 30


def test_seed_is_idempotent(db_session):
    seed_all(db_session)
    seed_all(db_session)
    assert db_session.scalar(select(func.count()).select_from(Restaurant)) == 5
    assert db_session.scalar(select(func.count()).select_from(Food)) == 30


def test_seed_keeps_persian_text_intact(db_session):
    seed_all(db_session)
    names = set(db_session.scalars(select(Food.name)))
    assert {"چیزبرگر", "پیتزا مخصوص", "سالاد سزار", "فیله سوخاری"} <= names