from pydantic import BaseModel

from app.schemas.common import UTCDateTime


class DashboardStats(BaseModel):
    total_documents: int
    ready_documents: int
    processing_documents: int  # uploaded + processing
    failed_documents: int


class ActivityItem(BaseModel):
    type: str  # "upload" | "question"
    title: str
    timestamp: UTCDateTime


class DatePoint(BaseModel):
    date: str  # YYYY-MM-DD (UTC)
    count: int


class StatusPoint(BaseModel):
    status: str
    count: int


class AnalyticsOverview(BaseModel):
    uploads_over_time: list[DatePoint]
    status_distribution: list[StatusPoint]
    question_activity: list[DatePoint]
