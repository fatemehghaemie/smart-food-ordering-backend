from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User, UserRole
from app.schemas.user import UserCreate
from app.security import hash_password, verify_password


class EmailAlreadyRegisteredError(Exception):
    """Raised when registering with an email that already exists."""


class InvalidCredentialsError(Exception):
    """Raised when email/password do not match a user."""


def _get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def register_user(db: Session, data: UserCreate) -> User:
    email = data.email.strip().lower()
    if _get_user_by_email(db, email) is not None:
        raise EmailAlreadyRegisteredError(email)

    user = User(
        name=data.name.strip(),
        email=email,
        hashed_password=hash_password(data.password),
        role=UserRole.CUSTOMER,  # public registration never grants ADMIN
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # race condition: same email inserted concurrently
        db.rollback()
        raise EmailAlreadyRegisteredError(email)
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = _get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        # Same error for both cases: don't reveal which emails exist.
        raise InvalidCredentialsError()
    return user