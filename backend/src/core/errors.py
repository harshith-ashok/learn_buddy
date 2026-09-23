from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base for domain/API errors that carry a stable `code` for clients.

    Route handlers and domain code raise this (or a subclass) instead of a
    bare `HTTPException`; the registered handler turns it into the
    `{code, message}` envelope.
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    """A requested resource does not exist, or is not owned by the caller."""

    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None) -> None:
        super().__init__("not_found", message, status.HTTP_404_NOT_FOUND, details)


class UnauthorizedError(AppError):
    """Missing or invalid credentials."""

    def __init__(self, message: str = "Not authenticated", details: dict[str, Any] | None = None) -> None:
        super().__init__("unauthorized", message, status.HTTP_401_UNAUTHORIZED, details)


class ForbiddenError(AppError):
    """Authenticated, but not allowed to access this resource."""

    def __init__(self, message: str = "Forbidden", details: dict[str, Any] | None = None) -> None:
        super().__init__("forbidden", message, status.HTTP_403_FORBIDDEN, details)


class ConflictError(AppError):
    """The request conflicts with existing state (e.g. duplicate email)."""

    def __init__(self, message: str = "Conflict", details: dict[str, Any] | None = None) -> None:
        super().__init__("conflict", message, status.HTTP_409_CONFLICT, details)


class RateLimitedError(AppError):
    """Too many requests in the current rate-limit window."""

    def __init__(
        self, message: str = "Rate limit exceeded, try again later", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__("rate_limited", message, status.HTTP_429_TOO_MANY_REQUESTS, details)


class LLMError(AppError):
    """Ollama Cloud call failed (transport error, non-2xx, or bad output)
    after retries. Never silently retried into a guess — callers treat
    this as a hard failure of whatever step invoked the model.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("llm_error", message, status.HTTP_502_BAD_GATEWAY, details)


def _envelope(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message}
    if details:
        body["details"] = details
    return body


def register_error_handlers(app: FastAPI) -> None:
    """Attach handlers so every error path returns `{code, message}` JSON."""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic's `.errors()` echoes the raw submitted value back in
        # `input` by default — for a field like `password` (e.g. a
        # too-short one on /auth/register), that puts the student's actual
        # password in the response body. Stripped for every field, not
        # just known-sensitive ones, since a future field being sensitive
        # shouldn't depend on someone remembering to add it to a list.
        errors = [{k: v for k, v in error.items() if k != "input"} for error in exc.errors()]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_envelope("validation_error", "Request validation failed", {"errors": errors}),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope("http_error", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("internal_error", "An unexpected error occurred"),
        )
