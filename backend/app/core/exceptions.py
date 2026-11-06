import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception for domain errors."""

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str | None = None,
        extra: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code or "APP_ERROR"
        self.extra = extra or {}
        self.headers = headers


class AuthenticationError(AppException):
    """Raised when authentication credentials are missing, invalid, or expired."""

    def __init__(
        self,
        detail: str = "Could not validate credentials",
        error_code: str = "UNAUTHORIZED",
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code,
            extra=extra,
            headers=headers or {"WWW-Authenticate": "Bearer"},
        )


async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.warning("Application exception: %s (code: %s)", exc.detail, exc.error_code)
    content: dict[str, Any] = {
        "detail": exc.detail,
        "error_code": exc.error_code,
    }
    if exc.extra:
        content["extra"] = exc.extra
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=exc.headers,
    )


async def http_exception_handler(
    _: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle standard HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request payload / parameter validation errors."""
    logger.info("Request validation failed: %s", exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": "Validation error",
            "errors": jsonable_encoder(exc.errors()),
        },
    )


async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected internal server errors."""
    logger.exception("Unhandled server exception: %s", str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
