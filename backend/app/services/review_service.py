"""Review schedules, completion and history.

Date policy: the server works in UTC. "Today" is the UTC calendar date (`utcnow().date()`), review dates are plain dates, and
timestamps are stored as naive UTC and sent with a trailing Z. A review date therefore rolls over at 00:00 UTC for everybody.

Status rules (derived on every read, nothing is stored or updated by a scheduler):
  in_review      - someone started a review that has not been completed (explicit flag)
  not_scheduled  - no next review date and never reviewed
  reviewed       - no next review date, but a review has been completed
  overdue        - next review date is before today
  due            - next review date is today or within the next REVIEW_DUE_SOON_DAYS days
  upcoming       - next review date is further away
Transitions: schedule/PUT sets dates; start -> in_review; complete -> history row, in_review cleared, next date = given date,
else today + interval, else none (reviewed); DELETE clears the schedule (history is kept)."""

from datetime import date, timedelta

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, bad_request
from app.models.document import Document, DocumentVersion
from app.models.knowledge import CollectionDocument
from app.models.review import DocumentReview, ReviewHistory
from app.models.user import User
from app.schemas.reviews import PersonOut, ReviewCompleteIn, ReviewHistoryOut, ReviewOut, ReviewScheduleIn
from app.services import access_service
from app.utils.time import utcnow

MAX_YEARS_AHEAD = 10


def today() -> date:
    return utcnow().date()


def derive_status(next_date: date | None, in_review: bool, last_reviewed_at, on: date | None = None, soon_days: int | None = None) -> str:
    on = on or today()
    soon = settings.review_due_soon_days if soon_days is None else soon_days
    if in_review:
        return "in_review"
    if next_date is None:
        return "reviewed" if last_reviewed_at else "not_scheduled"
    if next_date < on:
        return "overdue"
    if next_date <= on + timedelta(days=soon):
        return "due"
    return "upcoming"


def _status_case(on: date):
    soon = on + timedelta(days=settings.review_due_soon_days)
    r = DocumentReview
    return case(
        (r.in_review.is_(True), "in_review"),
        (and_(r.next_review_date.is_(None), r.last_reviewed_at.is_not(None)), "reviewed"),
        (r.next_review_date.is_(None), "not_scheduled"),
        (r.next_review_date < on, "overdue"),
        (r.next_review_date <= soon, "due"),
        else_="upcoming",
    )


def _validate_date(value: date | None, field: str = "next_review_date") -> None:
    if value is None:
        return
    on = today()
    if value < on:
        raise AppError(422, "DATE_IN_PAST", f"{field} must be today or later.")
    if value > on + timedelta(days=365 * MAX_YEARS_AHEAD):
        raise AppError(422, "DATE_TOO_FAR", f"{field} cannot be more than {MAX_YEARS_AHEAD} years ahead.")


# --------------------------------------------------------------- output
def _people(db: Session, ids: set) -> dict[int, PersonOut]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {u.id: PersonOut(id=u.id, name=u.name) for u in db.scalars(select(User).where(User.id.in_(ids)))}


def _out_many(db: Session, user: User, pairs: list[tuple[Document, DocumentReview | None]]) -> list[ReviewOut]:
    """Builds outputs for many documents with a constant number of queries."""
    people = _people(db, {x for _, r in pairs if r for x in (r.assigned_reviewer_id, r.last_reviewed_by)})
    vids = {d.current_version_id for d, _ in pairs} | {r.last_reviewed_version_id for _, r in pairs if r}
    numbers = dict(db.execute(select(DocumentVersion.id, DocumentVersion.version_number).where(DocumentVersion.id.in_([v for v in vids if v] or [0]))).all()) if vids else {}
    roles = access_service.document_roles(db, user.id, [d.id for d, _ in pairs])
    on = today()
    out = []
    for d, r in pairs:
        status = derive_status(r.next_review_date if r else None, bool(r and r.in_review), r.last_reviewed_at if r else None, on)
        out.append(
            ReviewOut(
                document_id=d.id, title=d.original_filename, version_number=numbers.get(d.current_version_id), status=status,
                interval_days=r.interval_days if r else None, next_review_date=r.next_review_date if r else None,
                days_until_due=(r.next_review_date - on).days if r and r.next_review_date else None,
                assigned_reviewer=people.get(r.assigned_reviewer_id) if r else None, notes=r.notes if r else None, in_review=bool(r and r.in_review),
                last_reviewed_at=r.last_reviewed_at if r else None, last_reviewed_by=people.get(r.last_reviewed_by) if r else None,
                last_outcome=r.last_outcome if r else None, last_reviewed_version_number=numbers.get(r.last_reviewed_version_id) if r else None,
                version_changed_since_review=bool(r and r.last_reviewed_version_id and r.last_reviewed_version_id != d.current_version_id),
                role=roles.get(d.id, "viewer"),
            )
        )
    return out


def _row(db: Session, document_id: int) -> DocumentReview | None:
    return db.scalar(select(DocumentReview).where(DocumentReview.document_id == document_id))


def _get_or_create(db: Session, document_id: int) -> DocumentReview:
    row = _row(db, document_id)
    if row is None:
        row = DocumentReview(document_id=document_id)
        db.add(row)
        db.flush()
    return row


# ------------------------------------------------------- single document
def get_review(db: Session, user: User, document_id: int) -> ReviewOut:
    doc, _ = access_service.get_document(db, user.id, document_id)
    return _out_many(db, user, [(doc, _row(db, doc.id))])[0]


def configure(db: Session, user: User, document_id: int, body: ReviewScheduleIn) -> ReviewOut:
    doc, _ = access_service.get_document(db, user.id, document_id, need="editor")
    sent = body.model_fields_set
    if not sent:
        raise bad_request("NOTHING_TO_UPDATE", "Provide an interval, a review date, a reviewer or notes.")
    _validate_date(body.next_review_date)
    row = _get_or_create(db, doc.id)
    if "assigned_reviewer_id" in sent:
        rid = body.assigned_reviewer_id
        if rid is not None:
            target = db.get(User, rid)
            role = access_service.document_roles(db, rid, [doc.id]).get(doc.id) if target and target.is_active else None
            if role not in ("owner", "editor"):  # only people who may manage the document can be asked to review it
                raise AppError(422, "INVALID_REVIEWER", "The reviewer must be an active user with editor access to this document.")
        row.assigned_reviewer_id = rid
    if "interval_days" in sent:
        row.interval_days = body.interval_days
    if "next_review_date" in sent:
        row.next_review_date = body.next_review_date
    elif "interval_days" in sent and body.interval_days and row.next_review_date is None:
        row.next_review_date = today() + timedelta(days=body.interval_days)  # a new interval with no date starts counting today
    if "notes" in sent:
        row.notes = body.notes
    db.commit()
    return get_review(db, user, doc.id)


def unschedule(db: Session, user: User, document_id: int) -> ReviewOut:
    """Clears the schedule (dates, interval, reviewer, in-review flag). Review history is kept."""
    doc, _ = access_service.get_document(db, user.id, document_id, need="editor")
    row = _row(db, doc.id)
    if row:
        row.next_review_date = row.interval_days = row.assigned_reviewer_id = None
        row.in_review = False
        db.commit()
    return get_review(db, user, doc.id)


def start(db: Session, user: User, document_id: int) -> ReviewOut:
    doc, _ = access_service.get_document(db, user.id, document_id, need="editor")
    row = _get_or_create(db, doc.id)
    if row.in_review:
        raise AppError(409, "ALREADY_IN_REVIEW", "A review of this document is already in progress.")
    row.in_review, row.in_review_started_by, row.in_review_started_at = True, user.id, utcnow()
    db.commit()
    return get_review(db, user, doc.id)


def complete(db: Session, user: User, document_id: int, body: ReviewCompleteIn) -> ReviewOut:
    """Records a completed review. The reviewer is ALWAYS the authenticated user; it is not an input. The reviewed version is
    the document's current version at this moment and is stored in the history row."""
    doc, _ = access_service.get_document(db, user.id, document_id, need="editor")
    _validate_date(body.next_review_date)
    row = _get_or_create(db, doc.id)
    version = db.get(DocumentVersion, doc.current_version_id) if doc.current_version_id else None
    now = utcnow()
    nxt = body.next_review_date or ((now.date() + timedelta(days=row.interval_days)) if row.interval_days else None)
    db.add(
        ReviewHistory(
            document_id=doc.id, version_id=version.id if version else None, version_number=version.version_number if version else None,
            reviewer_id=user.id, reviewed_at=now, outcome=body.outcome, notes=body.notes, previous_next_review_date=row.next_review_date, next_review_date=nxt,
        )
    )
    row.last_reviewed_at, row.last_reviewed_by, row.last_outcome = now, user.id, body.outcome
    row.last_reviewed_version_id = version.id if version else None
    row.next_review_date = nxt
    row.in_review = False
    db.commit()
    return get_review(db, user, doc.id)


def history(db: Session, user: User, document_id: int, page: int, page_size: int) -> tuple[list[ReviewHistoryOut], int]:
    doc, _ = access_service.get_document(db, user.id, document_id)
    stmt = select(ReviewHistory).where(ReviewHistory.document_id == doc.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(db.scalars(stmt.order_by(ReviewHistory.reviewed_at.desc(), ReviewHistory.id.desc()).offset((page - 1) * page_size).limit(page_size)))
    people = _people(db, {r.reviewer_id for r in rows})
    return [
        ReviewHistoryOut(id=r.id, document_id=r.document_id, version_id=r.version_id, version_number=r.version_number, reviewer=people.get(r.reviewer_id), reviewed_at=r.reviewed_at,
                         outcome=r.outcome, notes=r.notes, previous_next_review_date=r.previous_next_review_date, next_review_date=r.next_review_date)
        for r in rows
    ], total


# ------------------------------------------------------------ dashboard
def _accessible_reviews(user: User):
    return select(Document, DocumentReview).join(DocumentReview, DocumentReview.document_id == Document.id).where(Document.id.in_(access_service.readable_document_ids(user.id)))


def list_reviews(db: Session, user: User, *, status: str | None, collection_id: int | None, due_before: date | None, due_after: date | None,
                 reviewer_id: int | None, search: str | None, page: int, page_size: int, sort: str = "due"):
    stmt = _accessible_reviews(user)
    on = today()
    if status:
        if status == "not_scheduled":
            return [], 0
        stmt = stmt.where(_status_case(on) == status)
    if collection_id is not None:
        access_service.get_collection(db, user.id, collection_id)
        stmt = stmt.where(Document.id.in_(select(CollectionDocument.document_id).where(CollectionDocument.collection_id == collection_id)))
    if due_before:
        stmt = stmt.where(DocumentReview.next_review_date <= due_before)
    if due_after:
        stmt = stmt.where(DocumentReview.next_review_date >= due_after)
    if reviewer_id is not None:
        stmt = stmt.where(DocumentReview.assigned_reviewer_id == reviewer_id)
    if search:
        esc = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = stmt.where(Document.original_filename.ilike(f"%{esc}%", escape="\\"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    if sort == "title":
        order = (Document.original_filename.asc(), Document.id)
    else:  # undated items last, then soonest first
        order = (DocumentReview.next_review_date.is_(None), DocumentReview.next_review_date.asc(), Document.id)
    rows = db.execute(stmt.order_by(*order).offset((page - 1) * page_size).limit(page_size)).all()
    return _out_many(db, user, [(d, r) for d, r in rows]), total


def summary(db: Session, user: User) -> dict:
    on = today()
    counts = dict(db.execute(select(_status_case(on), func.count()).join(Document, Document.id == DocumentReview.document_id).where(Document.id.in_(access_service.readable_document_ids(user.id))).group_by(_status_case(on))).all())
    since = utcnow() - timedelta(days=30)
    base = select(ReviewHistory).where(ReviewHistory.document_id.in_(access_service.readable_document_ids(user.id)))
    completed = db.scalar(select(func.count()).select_from(base.where(ReviewHistory.reviewed_at >= since).subquery())) or 0
    recent_rows = list(db.scalars(base.order_by(ReviewHistory.reviewed_at.desc(), ReviewHistory.id.desc()).limit(8)))
    titles = dict(db.execute(select(Document.id, Document.original_filename).where(Document.id.in_([r.document_id for r in recent_rows] or [0]))).all())
    people = _people(db, {r.reviewer_id for r in recent_rows})
    recent = [
        {"document_id": r.document_id, "title": titles.get(r.document_id), "version_number": r.version_number, "outcome": r.outcome, "reviewed_at": r.reviewed_at.isoformat() + "Z",
         "reviewer": people[r.reviewer_id].model_dump() if r.reviewer_id in people else None}
        for r in recent_rows
    ]
    scheduled = counts.get("upcoming", 0) + counts.get("due", 0) + counts.get("overdue", 0) + _scheduled_in_review(db, user)
    return {"today": on, "due_soon_days": settings.review_due_soon_days, "scheduled": scheduled, "upcoming": counts.get("upcoming", 0), "due": counts.get("due", 0),
            "overdue": counts.get("overdue", 0), "in_review": counts.get("in_review", 0), "completed_last_30_days": completed, "recent": recent}


def _scheduled_in_review(db: Session, user: User) -> int:
    """Documents currently in review that also have a next review date, so `scheduled` counts every dated document once."""
    stmt = select(func.count()).select_from(DocumentReview).where(DocumentReview.in_review.is_(True), DocumentReview.next_review_date.is_not(None), DocumentReview.document_id.in_(access_service.readable_document_ids(user.id)))
    return db.scalar(stmt) or 0
