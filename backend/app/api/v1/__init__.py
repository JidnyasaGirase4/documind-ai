from fastapi import APIRouter

from app.api.v1 import analytics, auth, conversations, dashboard, documents, messages, settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(documents.router)
api_router.include_router(conversations.router)
api_router.include_router(messages.router)
api_router.include_router(analytics.router)
api_router.include_router(settings.router)
