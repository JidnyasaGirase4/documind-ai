from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import AnalyticsOverview
from app.services import dashboard_service, quality_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return dashboard_service.analytics(db, user)


@router.get("/feedback")
def feedback(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The caller's own thumbs-up/down feedback: totals, daily trend, reasons for thumbs-downs and recent comments."""
    return quality_service.feedback_summary(db, user)


@router.get("/queries")
def queries(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The caller's own question statistics: outcomes, latency percentiles and failure categories (measured from the query log)."""
    return quality_service.query_summary(db, user)


@router.get("/evaluations")
def evaluations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Latest and recent RAG evaluation runs. Runs use the synthetic evaluation dataset only, never user documents."""
    return quality_service.evaluation_overview(db)


@router.get("/evaluations/{run_id}")
def evaluation(run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return quality_service.evaluation_detail(db, run_id)
