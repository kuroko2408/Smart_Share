"""Tests for application settings and configuration validation."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_settings() -> None:
    """Test default values for configuration."""
    settings = Settings(
        APP_NAME="Smart Share",
        APP_ENV="development",
        API_V1_PREFIX="/api/v1",
        DATABASE_URL="",
    )
    assert settings.APP_NAME == "Smart Share"
    assert settings.APP_ENV == "development"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.LOG_LEVEL == "INFO"
    assert settings.CORS_ORIGINS == ["http://localhost:5173"]
    assert settings.async_database_url is None
    assert settings.sync_database_url is None


def test_cors_origins_parsing_comma_separated() -> None:
    """Test parsing CORS_ORIGINS from a comma-separated string."""
    settings = Settings(
        CORS_ORIGINS="http://localhost:5173, https://example.com , http://127.0.0.1:3000"
    )
    assert settings.CORS_ORIGINS == [
        "http://localhost:5173",
        "https://example.com",
        "http://127.0.0.1:3000",
    ]


def test_cors_origins_parsing_json_array() -> None:
    """Test parsing CORS_ORIGINS from a JSON array string."""
    settings = Settings(
        CORS_ORIGINS='["http://localhost:5173", "https://app.domain.com"]'
    )
    assert settings.CORS_ORIGINS == ["http://localhost:5173", "https://app.domain.com"]


def test_cors_origins_parsing_empty() -> None:
    """Test parsing empty CORS_ORIGINS string."""
    settings = Settings(CORS_ORIGINS="")
    assert settings.CORS_ORIGINS == []


def test_log_level_validation() -> None:
    """Test that valid log levels are accepted and case-normalized."""
    s1 = Settings(LOG_LEVEL="debug")
    assert s1.LOG_LEVEL == "DEBUG"

    s2 = Settings(LOG_LEVEL="WARNING")
    assert s2.LOG_LEVEL == "WARNING"

    with pytest.raises(ValidationError):
        Settings(LOG_LEVEL="INVALID_LEVEL")


def test_database_url_helpers() -> None:
    """Test async and sync database URL helpers."""
    # Standard postgresql:// -> postgresql+asyncpg://
    s = Settings(DATABASE_URL="postgresql://user:pass@localhost:5432/mydb")
    assert s.async_database_url == "postgresql+asyncpg://user:pass@localhost:5432/mydb"
    assert s.sync_database_url == "postgresql://user:pass@localhost:5432/mydb"

    # postgresql+asyncpg:// -> postgresql+psycopg:// for sync
    s_async = Settings(
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/mydb"
    )
    assert (
        s_async.async_database_url
        == "postgresql+asyncpg://user:pass@localhost:5432/mydb"
    )
    assert (
        s_async.sync_database_url
        == "postgresql+psycopg://user:pass@localhost:5432/mydb"
    )
