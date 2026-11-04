"""Smart Share FastAPI Application Entrypoint."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.schemas.health import HealthResponse

# Initialize structured logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan lifecycle manager."""
    logger.info(
        "Starting up %s (env=%s, api_prefix=%s)",
        settings.APP_NAME,
        settings.APP_ENV,
        settings.API_V1_PREFIX,
    )
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="Location-based cab pooling platform backend.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Register CORS middleware
    # Specific origins from configuration — never wildcard when credentials are enabled
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register exception handlers
    register_exception_handlers(app)

    # Register API v1 versioned router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Health endpoint exposed at root level
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check() -> HealthResponse:
        """Root health check endpoint."""
        return HealthResponse(status="ok", service="smart-share-backend")

    # Root informational endpoint
    @app.get("/", tags=["Root"])
    async def root_info() -> dict[str, str]:
        """Root service metadata."""
        return {
            "name": settings.APP_NAME,
            "environment": settings.APP_ENV,
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_application()
