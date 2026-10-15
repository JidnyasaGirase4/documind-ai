"""One error shape for the whole API: { "error": { "code", "message", "details" } }."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("documind")


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def bad_request(code: str, message: str, details=None) -> AppError:
    return AppError(400, code, message, details)


def unauthorized(code: str = "NOT_AUTHENTICATED", message: str = "Authentication is required.") -> AppError:
    return AppError(401, code, message)


def not_found(what: str = "Resource") -> AppError:
    return AppError(404, "NOT_FOUND", f"{what} not found.")


def _body(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(status_code=exc.status_code, content=_body(exc.code, exc.message, exc.details), headers=headers)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_: Request, exc: StarletteHTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, f"HTTP_{exc.status_code}")
        return JSONResponse(status_code=exc.status_code, content=_body(code, message))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        details = []
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
            details.append({"field": ".".join(loc) or None, "message": err.get("msg", "Invalid value")})
        summary = "; ".join(f"{d['field']}: {d['message']}" if d["field"] else d["message"] for d in details) or "Invalid request."
        return JSONResponse(status_code=422, content=_body("VALIDATION_ERROR", summary, details))

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception):
        # The traceback goes to the server log only, never to the client.
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(status_code=500, content=_body("INTERNAL_ERROR", "Something went wrong on the server."))
