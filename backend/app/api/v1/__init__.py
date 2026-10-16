from fastapi import APIRouter

from app.api.v1 import analytics, auth, conflicts, conversations, dashboard, documents, jobs, knowledge, messages, reviews, search, settings, versions

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(documents.router)
api_router.include_router(versions.router)
api_router.include_router(reviews.router)
api_router.include_router(conflicts.router)
api_router.include_router(jobs.router)
api_router.include_router(knowledge.router)
api_router.include_router(search.router)
api_router.include_router(conversations.router)
api_router.include_router(messages.router)
api_router.include_router(analytics.router)
api_router.include_router(settings.router)
