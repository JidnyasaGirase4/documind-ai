"""Answer feedback, per-question query logs and RAG evaluation runs."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.time import utcnow

RATING_UP = "up"
RATING_DOWN = "down"
FEEDBACK_CATEGORIES = ("inaccurate", "missing_information", "wrong_source", "unclear", "other")

OUTCOME_ANSWERED = "answered"
OUTCOME_INSUFFICIENT = "insufficient_evidence"
OUTCOME_ERROR = "error"


class MessageFeedback(Base):
    """One user's thumbs-up/down (and optional note) on one assistant message."""

    __tablename__ = "message_feedback"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_feedback_message_user"), Index("ix_feedback_user_created", "user_id", "created_at"))

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    rating: Mapped[str] = mapped_column(String(10))  # up | down
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)  # why a thumbs-down was given
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class QueryLog(Base):
    """One row per question asked, including the ones that failed: the source of the latency and failure statistics."""

    __tablename__ = "query_logs"
    __table_args__ = (Index("ix_query_logs_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)  # the assistant message
    outcome: Mapped[str] = mapped_column(String(30))  # answered | insufficient_evidence | error
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer)
    document_count: Mapped[int] = mapped_column(Integer, default=0)  # documents in the searched scope
    source_count: Mapped[int] = mapped_column(Integer, default=0)  # passages sent to the model
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class EvalRun(Base):
    """One execution of the evaluation dataset against the real pipeline. Contains only the synthetic dataset's data."""

    __tablename__ = "eval_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running | completed | failed
    dataset_name: Mapped[str] = mapped_column(String(100))
    dataset_version: Mapped[str] = mapped_column(String(50))
    dataset_hash: Mapped[str] = mapped_column(String(64))  # sha256 of the dataset file: proves which questions were used
    mode: Mapped[str] = mapped_column(String(30))  # full | retrieval_only
    judge: Mapped[str] = mapped_column(String(20))  # heuristic | llm | none (how faithfulness was scored)
    k: Mapped[int] = mapped_column(Integer)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # models, chunking and retrieval settings used
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # aggregates, each tagged with how it was obtained
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    results: Mapped[list["EvalResult"]] = relationship(back_populates="run", cascade="all, delete-orphan", passive_deletes=True, order_by="EvalResult.id")


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("eval_runs.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(50))
    question: Mapped[str] = mapped_column(Text)
    answerable: Mapped[bool] = mapped_column(Boolean, default=True)
    expected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevant: Mapped[list | None] = mapped_column(JSON, nullable=True)  # labelled [{document, page}]
    retrieved: Mapped[list | None] = mapped_column(JSON, nullable=True)  # top-K [{document, page, similarity}]
    cited: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{document, page, correct}]
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str] = mapped_column(String(30))  # answered | insufficient_evidence | error | skipped
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    precision_at_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall_at_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    citation_correctness: Mapped[float | None] = mapped_column(Float, nullable=True)
    faithfulness: Mapped[float | None] = mapped_column(Float, nullable=True)
    faithfulness_method: Mapped[str | None] = mapped_column(String(20), nullable=True)  # lexical | llm_judge
    keyword_recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    correct_abstention: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    retrieval_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    run: Mapped[EvalRun] = relationship(back_populates="results")
