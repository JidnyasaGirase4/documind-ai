"""Statistics behind the RAG quality page.

Everything here is read from stored rows: the user's own feedback and query log (scoped to the user) and the
evaluation runs (which contain only the synthetic evaluation dataset, no user documents). Nothing is estimated here;
the evaluation metrics carry a `kind` that says how each value was obtained (measured / automated_estimate / llm_judge)."""

import math
from collections import Counter, defaultdict
from datetime import timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.conversation import Message
from app.models.quality import OUTCOME_ANSWERED, OUTCOME_ERROR, OUTCOME_INSUFFICIENT, RATING_DOWN, RATING_UP, EvalResult, EvalRun, MessageFeedback, QueryLog
from app.models.user import User
from app.utils.time import utcnow

DAYS = 30

FAILURE_LABELS = {
    "insufficient_evidence": "Not enough evidence in documents",
    "llm_unavailable": "AI provider unavailable or timed out",
    "embedding_unavailable": "Embedding model unavailable",
    "document_problem": "Selected document missing or not ready",
    "other_error": "Other error",
}


def _failure_category(outcome: str, code: str | None) -> str:
    if outcome == OUTCOME_INSUFFICIENT:
        return "insufficient_evidence"
    code = code or ""
    if code.startswith("LLM_"):
        return "llm_unavailable"
    if code.startswith("EMBEDDING"):
        return "embedding_unavailable"
    if code in {"DOCUMENT_NOT_FOUND", "DOCUMENT_NOT_READY", "NO_READY_DOCUMENTS", "TOO_MANY_DOCUMENTS"}:
        return "document_problem"
    return "other_error"


def _percentile(values: list[int], q: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(0, math.ceil(q * len(ordered)) - 1)  # nearest-rank method
    return ordered[rank]


def _since():
    return (utcnow() - timedelta(days=DAYS - 1)).replace(hour=0, minute=0, second=0, microsecond=0)


def _days():
    today = utcnow().date()
    return [str(today - timedelta(days=i)) for i in range(DAYS - 1, -1, -1)]


def feedback_summary(db: Session, user: User) -> dict:
    rows = db.execute(
        select(MessageFeedback, Message.conversation_id)
        .join(Message, Message.id == MessageFeedback.message_id)
        .where(MessageFeedback.user_id == user.id, MessageFeedback.created_at >= _since())
        .order_by(desc(MessageFeedback.updated_at))
    ).all()
    up = sum(1 for f, _ in rows if f.rating == RATING_UP)
    down = sum(1 for f, _ in rows if f.rating == RATING_DOWN)
    per_day: dict[str, Counter] = defaultdict(Counter)
    for f, _ in rows:
        per_day[str(f.created_at.date())][f.rating] += 1
    categories = Counter(f.category or "unspecified" for f, _ in rows if f.rating == RATING_DOWN)
    return {
        "days": DAYS,
        "total": len(rows),
        "up": up,
        "down": down,
        "satisfaction": round(up / len(rows), 4) if rows else None,
        "by_day": [{"date": d, "up": per_day[d][RATING_UP], "down": per_day[d][RATING_DOWN]} for d in _days()],
        "down_categories": [{"category": c, "count": n} for c, n in categories.most_common()],
        "recent_comments": [
            {"message_id": f.message_id, "conversation_id": cid, "rating": f.rating, "category": f.category, "comment": f.comment, "created_at": f.updated_at}
            for f, cid in rows
            if f.comment
        ][:10],
    }


def query_summary(db: Session, user: User) -> dict:
    logs = list(db.scalars(select(QueryLog).where(QueryLog.user_id == user.id, QueryLog.created_at >= _since()).order_by(QueryLog.id)))
    answered = [q for q in logs if q.outcome == OUTCOME_ANSWERED]
    insufficient = [q for q in logs if q.outcome == OUTCOME_INSUFFICIENT]
    errors = [q for q in logs if q.outcome == OUTCOME_ERROR]
    completed = answered + insufficient
    latencies = [q.latency_ms for q in completed]
    per_day: dict[str, list[int]] = defaultdict(list)
    for q in completed:
        per_day[str(q.created_at.date())].append(q.latency_ms)
    categories = Counter(_failure_category(q.outcome, q.error_code) for q in logs if q.outcome != OUTCOME_ANSWERED)
    total = len(logs)
    return {
        "days": DAYS,
        "total_questions": total,
        "answered": len(answered),
        "insufficient_evidence": len(insufficient),
        "errors": len(errors),
        "failure_rate": round(len(errors) / total, 4) if total else None,  # questions that returned an error
        "insufficient_rate": round(len(insufficient) / total, 4) if total else None,
        "latency_ms": {
            "count": len(latencies),
            "avg": round(sum(latencies) / len(latencies)) if latencies else None,
            "p50": _percentile(latencies, 0.5),
            "p95": _percentile(latencies, 0.95),
            "max": max(latencies) if latencies else None,
        },
        "latency_by_day": [
            {"date": d, "avg_ms": round(sum(per_day[d]) / len(per_day[d])) if per_day[d] else None, "count": len(per_day[d])} for d in _days()
        ],
        "failure_categories": [{"category": c, "label": FAILURE_LABELS[c], "count": n} for c, n in categories.most_common()],
    }


def _run_out(run: EvalRun) -> dict:
    return {
        "id": run.id,
        "status": run.status,
        "dataset_name": run.dataset_name,
        "dataset_version": run.dataset_version,
        "dataset_hash": run.dataset_hash,
        "mode": run.mode,
        "judge": run.judge,
        "k": run.k,
        "config": run.config or {},
        "metrics": run.metrics or {},
        "error": run.error,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }


def evaluation_overview(db: Session) -> dict:
    runs = list(db.scalars(select(EvalRun).order_by(desc(EvalRun.id)).limit(10)))
    completed = [r for r in runs if r.status == "completed"]
    return {"latest": _run_out(completed[0]) if completed else None, "history": [_run_out(r) for r in runs]}


def evaluation_detail(db: Session, run_id: int) -> dict:
    run = db.get(EvalRun, run_id)
    if run is None:
        raise AppError(404, "NOT_FOUND", "Evaluation run not found.")
    results = [
        {
            "question_id": r.question_id,
            "category": r.category,
            "question": r.question,
            "answerable": r.answerable,
            "expected_answer": r.expected_answer,
            "relevant": r.relevant or [],
            "retrieved": r.retrieved or [],
            "cited": r.cited or [],
            "answer": r.answer,
            "outcome": r.outcome,
            "error": r.error,
            "precision_at_k": r.precision_at_k,
            "recall_at_k": r.recall_at_k,
            "citation_correctness": r.citation_correctness,
            "faithfulness": r.faithfulness,
            "faithfulness_method": r.faithfulness_method,
            "keyword_recall": r.keyword_recall,
            "correct_abstention": r.correct_abstention,
            "retrieval_ms": r.retrieval_ms,
            "latency_ms": r.latency_ms,
        }
        for r in db.scalars(select(EvalResult).where(EvalResult.run_id == run_id).order_by(EvalResult.id))
    ]
    return {**_run_out(run), "results": results}
