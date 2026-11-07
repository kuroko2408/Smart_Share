"""Tests for application initialization, middleware, routing, and exception handling."""

import sys

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.exceptions import AppException
from app.main import app


def test_app_initialization(client: TestClient) -> None:
    """Verify application metadata and OpenAPI schema initialization."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Smart Share"
    assert "paths" in schema
    assert "/health" in schema["paths"]
    assert "/api/v1/health" in schema["paths"]


def test_root_endpoint(client: TestClient) -> None:
    """Verify root informational endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Smart Share"
    assert data["health"] == "/health"
    assert data["docs"] == "/docs"


def test_cors_headers_allowed_origin(client: TestClient) -> None:
    """Verify CORS preflight succeeds for allowed origin."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    )
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_headers_disallowed_origin(client: TestClient) -> None:
    """Verify CORS preflight does not reflect untrusted origins."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://unauthorized-domain.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # The header must not be set or must not match unauthorized origin
    assert (
        response.headers.get("access-control-allow-origin")
        != "http://unauthorized-domain.com"
    )


def test_app_exception_handler() -> None:
    """Verify custom AppException handler converts to expected JSON response."""
    test_app = app

    @test_app.get("/test-custom-error")
    def trigger_error() -> None:
        raise AppException(
            detail="Resource unavailable",
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
        )

    with TestClient(
        test_app, backend_options={"use_uvloop": sys.platform != "win32"}
    ) as tc:
        response = tc.get("/test-custom-error")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Resource unavailable"
        assert data["error_code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_database_dependency_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that get_db raises a clear RuntimeError when DATABASE_URL is unconfigured."""
    monkeypatch.setattr("app.core.database.async_session_factory", None)
    db_gen = get_db()
    with pytest.raises(RuntimeError) as exc_info:
        await anext(db_gen)
    assert "Database connection is not configured" in str(exc_info.value)
