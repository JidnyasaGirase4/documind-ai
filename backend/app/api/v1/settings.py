from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.settings import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/profile", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user)):
    return user


@router.patch("/profile", response_model=ProfileOut)
def update_profile(body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.name = body.name
    db.commit()
    db.refresh(user)
    return user
