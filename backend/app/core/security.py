"""Password hashing (Argon2id) and JWT access tokens."""

from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings
from app.core.errors import unauthorized

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: int, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    minutes = settings.jwt_access_token_expire_minutes if expires_minutes is None else expires_minutes
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=minutes)}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    """Returns the user id, or raises a 401 AppError."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm], options={"require": ["exp", "sub"]})
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise unauthorized("TOKEN_EXPIRED", "Your session has expired. Please sign in again.") from None
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized("INVALID_TOKEN", "Your session is not valid. Please sign in again.") from None
