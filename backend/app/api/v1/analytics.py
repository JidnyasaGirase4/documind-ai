from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import AnalyticsOverview
from app.services import dashboard_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return dashboard_service.analytics(db, user)
