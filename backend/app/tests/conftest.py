"""Pytest fixtures and configuration."""

from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from geoalchemy2 import Geography
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CheckConstraint

try:
    import uvloop
except ImportError:  # pragma: no cover - uvloop is unavailable on Windows
    uvloop = None

from app.main import app


@compiles(Geography, "sqlite")
def compile_geography_sqlite(element: Any, compiler: Any, **kw: Any) -> str:
    """Compile PostGIS Geography type to TEXT for in-memory SQLite testing."""
    return "TEXT"


@compiles(CheckConstraint, "sqlite")
def compile_check_constraint_sqlite(element: Any, compiler: Any, **kw: Any) -> str:
    """Strip PostgreSQL-specific ::geometry casts for SQLite in-memory DDL."""
    text_sql = compiler.sql_compiler.process(
        element.sqltext, include_table=False, literal_binds=True
    )
    text_sql = text_sql.replace("::geometry", "")
    preamble = compiler.define_constraint_preamble(element, **kw)
    return f"{preamble}CHECK ({text_sql})"


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
