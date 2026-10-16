import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.db.init_db import check_database
from app.services.embedding_service import get_embedder

logger = logging.getLogger("documind")


def _warm_up_embedder() -> None:
    try:
        get_embedder().embed(["warm up"])
        logger.info("Embedding model is loaded and ready")
    except Exception:
        logger.exception("Embedding warm-up failed; it will be retried on first use")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Load the embedding model in the background so the first upload or question is not slow.
    if settings.embedding_provider.lower() == "sentence_transformers":
        threading.Thread(target=_warm_up_embedder, daemon=True, name="embedder-warmup").start()
    stop = None
    if settings.worker_embedded:
        from app import worker  # imported lazily: the worker pulls in the whole processing pipeline

        _, stop = worker.start_embedded()
    try:
        yield
    finally:
        if stop is not None:
            stop.set()


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    production = settings.app_env == "production"

    app = FastAPI(
        lifespan=lifespan,
        title=settings.app_name,
        version="1.0.0",
        description="Backend for DocuMind AI: authenticated PDF upload, indexing and cited question answering.",
        # Interactive API docs are enabled in development only.
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,  # Bearer tokens travel in the Authorization header, not cookies
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    register_error_handlers(app)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if request.url.path.startswith("/api/"):
            # API responses can contain private data: never let a shared cache keep them.
            response.headers.setdefault("Cache-Control", "no-store")
        return response
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    def health():
        db_ok = check_database()
        return {"status": "ok" if db_ok else "degraded", "database": "ok" if db_ok else "unreachable"}

    return app


app = create_app()
