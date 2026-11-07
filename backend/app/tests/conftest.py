"""Pytest fixtures and configuration."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

try:
    import uvloop
except ImportError:  # pragma: no cover - uvloop is unavailable on Windows
    uvloop = None

from app.main import app


def pytest_asyncio_loop_factories(config, item):
    """Use uvloop; CPython 3.14's default loop stalls on worker thread callbacks."""
    if uvloop is None:
        return {}
    return {"uvloop": uvloop.new_event_loop}


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """Test client fixture configured with the FastAPI application."""
    with TestClient(
        app, backend_options={"use_uvloop": uvloop is not None}
    ) as test_client:
        yield test_client
