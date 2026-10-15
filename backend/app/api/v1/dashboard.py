from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import ActivityItem, DashboardStats
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return dashboard_service.stats(db, user)


@router.get("/activity", response_model=list[ActivityItem])
def activity(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return dashboard_service.activity(db, user)
