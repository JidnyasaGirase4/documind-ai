from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError, unauthorized
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.repositories import user_repository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.utils.rate_limit import rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])

# Verified against when the email is unknown, so unknown-email and wrong-password take similar time.
_DUMMY_HASH = hash_password("not-a-real-password-1")


@router.post("/register", response_model=UserOut, status_code=201, dependencies=[Depends(rate_limit("register", 10, 60))])
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if user_repository.get_by_email(db, body.email):
        raise AppError(409, "EMAIL_ALREADY_REGISTERED", "An account with this email already exists.")
    try:
        return user_repository.create(db, name=body.name, email=body.email, password_hash=hash_password(body.password))
    except IntegrityError:  # two registrations racing for the same email
        db.rollback()
        raise AppError(409, "EMAIL_ALREADY_REGISTERED", "An account with this email already exists.") from None


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit("login", 10, 60))])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = user_repository.get_by_email(db, body.email)
    if user is None:
        verify_password(body.password, _DUMMY_HASH)
        raise unauthorized("INVALID_CREDENTIALS", "Invalid email or password.")
    if not verify_password(body.password, user.password_hash) or not user.is_active:
        raise unauthorized("INVALID_CREDENTIALS", "Invalid email or password.")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
