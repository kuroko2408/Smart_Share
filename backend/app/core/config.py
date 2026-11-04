import json
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application settings
    APP_NAME: str = "Smart Share"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    # Format: postgresql+asyncpg://user:password@host:port/dbname
    DATABASE_URL: str = ""

    # Supabase authentication placeholders
    # NOTE: Do not assume Supabase uses a symmetric JWT secret.
    # Token verification must be selected based on project signing configuration (e.g. JWKS).
    SUPABASE_URL: str = ""
    SUPABASE_JWKS_URL: str = ""

    # Routing provider placeholders (e.g. OpenRouteService, OSRM, Google Maps)
    ROUTING_PROVIDER: str = ""
    ROUTING_API_KEY: str = ""

    # CORS origins (stored as a list of strings)
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL: str = "INFO"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from list, comma-separated string, or JSON array string."""
        if isinstance(v, str):
            trimmed = v.strip()
            if not trimmed:
                return []
            if trimmed.startswith("[") and trimmed.endswith("]"):
                try:
                    parsed = json.loads(trimmed)
                    if isinstance(parsed, list):
                        return [
                            str(item).strip() for item in parsed if str(item).strip()
                        ]
                except (json.JSONDecodeError, TypeError):
                    pass
            return [origin.strip() for origin in trimmed.split(",") if origin.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(item).strip() for item in v if str(item).strip()]
        return []

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate that LOG_LEVEL is a recognized Python logging level name."""
        allowed = {"DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL"}
        upper_v = v.upper().strip()
        if upper_v not in allowed:
            raise ValueError(
                f"Invalid LOG_LEVEL '{v}'. Allowed values: {', '.join(sorted(allowed))}"
            )
        return upper_v

    @property
    def async_database_url(self) -> str | None:
        """Get database URL adapted for asyncpg driver, or None if unconfigured."""
        if not self.DATABASE_URL or not self.DATABASE_URL.strip():
            return None
        url = self.DATABASE_URL.strip()
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str | None:
        """Get database URL adapted for sync driver (e.g. Alembic/psycopg), or None if unconfigured."""
        if not self.DATABASE_URL or not self.DATABASE_URL.strip():
            return None
        url = self.DATABASE_URL.strip()
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()


settings = get_settings()
