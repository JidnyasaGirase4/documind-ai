from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import page_of
from app.schemas.conflicts import AnalyzeIn, DecisionIn, DecisionOut, FindingOut, ReportOut
from app.services import conflict_service as svc
from app.utils.rate_limit import rate_limit

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.post("/analyze", response_model=ReportOut, status_code=202, dependencies=[Depends(rate_limit("conflicts", 10, 60))])
def analyze(body: AnalyzeIn, background: BackgroundTasks, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Owner/editor: look for POTENTIAL conflicts for one document or one collection. Runs in the background; poll the report.
    Findings are AI-assisted suggestions that need human review."""
    report = svc.start_analysis(db, user, body.document_id, body.collection_id)
    background.add_task(svc.run_report, report.id)
    return svc.report_out(report)


# Declared before "/{conflict_id}" so "reports" is never parsed as an id.
@router.get("/reports")
def list_reports(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = svc.list_reports(db, user, page, page_size)
    return page_of([ReportOut(**i).model_dump(mode="json") for i in items], total, page, page_size)


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.report_out(svc.get_report(db, user, report_id))


@router.get("")
def list_findings(
    review_status: Literal["pending", "confirmed", "not_conflict", "needs_review"] | None = None,
    assessment: Literal["potential_conflict", "needs_review"] | None = None,
    document_id: int | None = None,
    collection_id: int | None = None,
    report_id: int | None = None,
    stale: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Only findings whose two source documents the caller can still read."""
    items, total = svc.list_findings(db, user, review_status=review_status, assessment=assessment, document_id=document_id, collection_id=collection_id, report_id=report_id, stale=stale, page=page, page_size=page_size)
    return page_of([FindingOut(**i).model_dump(mode="json") for i in items], total, page, page_size)


@router.get("/{conflict_id}", response_model=FindingOut)
def get_finding(conflict_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.get_finding(db, user, conflict_id)


@router.patch("/{conflict_id}/decision", response_model=FindingOut)
def decide(conflict_id: int, body: DecisionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Owner/editor of both documents: confirmed / not a conflict / needs further review. Recorded with the user and time."""
    return svc.decide(db, user, conflict_id, body.decision, body.note)


@router.get("/{conflict_id}/decisions", response_model=list[DecisionOut])
def decisions(conflict_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.decisions(db, user, conflict_id)
