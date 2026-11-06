import asyncio
from logging.config import fileConfig

import geoalchemy2  # noqa: F401
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import settings

# Import Base from app.models to ensure all model definitions are registered on metadata
from app.models import Base

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate support
target_metadata = Base.metadata

# PostGIS system tables and managed schemas to exclude from autogenerate comparison
POSTGIS_SYSTEM_TABLES = {
    "spatial_ref_sys",
    "geography_columns",
    "geometry_columns",
    "raster_columns",
    "raster_overviews",
}


def include_object(
    object: object,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: object | None,
) -> bool:
    """Filter out PostGIS system objects and managed external schemas from migrations."""
    if type_ == "table":
        # Ignore PostGIS internal system tables
        if name in POSTGIS_SYSTEM_TABLES:
            return False
        # Ignore Supabase-managed auth schema and users table
        schema = getattr(object, "schema", None)
        if schema == "auth" or (name == "users" and schema == "auth"):
            return False
    return True


def get_async_database_url() -> str:
    """Retrieve async database URL from application settings."""
    url = settings.async_database_url
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Please configure DATABASE_URL in your environment before running migrations."
        )
    return url


def get_sync_database_url() -> str:
    """Retrieve sync database URL for offline migration generation."""
    url = settings.sync_database_url
    if not url:
        # Fallback to local default for offline SQL generation
        return "postgresql+psycopg://postgres:postgres@localhost:5433/smart_share"
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode without an active DB connection."""
    url = get_sync_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations on the provided connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with an async connection."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_async_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
