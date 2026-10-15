from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import unauthorized
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories import user_repository

_bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)) -> User:
    """Reusable dependency: resolves the Bearer token to an active user or raises 401."""
    if credentials is None or not credentials.credentials:
        raise unauthorized()
    user_id = decode_access_token(credentials.credentials)
    user = user_repository.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise unauthorized("INVALID_TOKEN", "Your session is not valid. Please sign in again.")
    return user
