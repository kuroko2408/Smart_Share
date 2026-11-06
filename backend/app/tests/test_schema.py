"""Tests for database schema constraints, indexes, and Alembic migration SQL."""

import subprocess
import sys
from pathlib import Path

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, PrimaryKeyConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.models import Base, Profile, RideRequest


def test_schema_tables_registered() -> None:
    """Verify that profiles and ride_requests are registered on Base metadata."""
    assert "profiles" in Base.metadata.tables
    assert "ride_requests" in Base.metadata.tables


def test_profile_constraints_and_columns() -> None:
    """Verify Profile table columns, primary key, check constraint, and foreign key."""
    table = Base.metadata.tables["profiles"]

    # Column existence and properties
    assert "id" in table.columns
    assert table.columns["id"].primary_key is True

    assert "display_name" in table.columns
    assert table.columns["display_name"].nullable is False
    assert table.columns["display_name"].server_default is not None

    assert "avatar_url" in table.columns
    assert table.columns["avatar_url"].nullable is True

    assert "created_at" in table.columns
    assert table.columns["created_at"].nullable is False

    assert "updated_at" in table.columns
    assert table.columns["updated_at"].nullable is False

    # Check constraint
    check_constraints = [c for c in table.constraints if isinstance(c, CheckConstraint)]
    chk_names = {c.name for c in check_constraints}
    assert "chk_profiles_display_name_length" in chk_names

    # Foreign key to auth.users(id) with CASCADE
    fk_constraints = [
        c for c in table.constraints if isinstance(c, ForeignKeyConstraint)
    ]
    assert len(fk_constraints) == 1
    fk = fk_constraints[0]
    assert fk.ondelete == "CASCADE"


def test_ride_request_constraints_and_indexes() -> None:
    """Verify RideRequest constraints, indexes, and spatial columns."""
    table = Base.metadata.tables["ride_requests"]

    # Required columns
    required_cols = [
        "id",
        "user_id",
        "pickup_location",
        "destination",
        "departure_earliest",
        "departure_latest",
        "seats_requested",
        "max_extra_minutes",
        "status",
        "created_at",
        "updated_at",
    ]
    for col in required_cols:
        assert col in table.columns
        assert table.columns[col].nullable is False

    # Optional columns
    assert table.columns["pickup_label"].nullable is True
    assert table.columns["destination_label"].nullable is True
    assert table.columns["expires_at"].nullable is True

    # Primary key
    pk_constraints = [
        c for c in table.constraints if isinstance(c, PrimaryKeyConstraint)
    ]
    assert len(pk_constraints) == 1

    # Foreign key to profiles(id) with CASCADE
    fk_constraints = [
        c for c in table.constraints if isinstance(c, ForeignKeyConstraint)
    ]
    assert len(fk_constraints) == 1
    assert fk_constraints[0].ondelete == "CASCADE"

    # Check constraints
    check_constraints = [c for c in table.constraints if isinstance(c, CheckConstraint)]
    chk_names = {c.name for c in check_constraints}
    expected_checks = {
        "chk_ride_requests_departure_window",
        "chk_ride_requests_seats",
        "chk_ride_requests_max_extra_minutes",
        "chk_ride_requests_status",
        "chk_ride_requests_distinct_endpoints",
        "chk_ride_requests_expiry_window",
    }
    assert expected_checks.issubset(chk_names)

    # Indexes
    index_names = {idx.name for idx in table.indexes}
    expected_indexes = {
        "idx_ride_requests_pickup_gist",
        "idx_ride_requests_destination_gist",
        "idx_ride_requests_user_id",
        "idx_ride_requests_active_departure",
        "idx_ride_requests_active_expiry",
    }
    assert expected_indexes.issubset(index_names)


def test_ddl_compilation_with_postgresql_dialect() -> None:
    """Verify that both models compile to valid PostgreSQL DDL without errors."""
    dialect = postgresql.dialect()

    profile_ddl = str(CreateTable(Profile.__table__).compile(dialect=dialect))
    assert "CREATE TABLE profiles" in profile_ddl
    assert "FOREIGN KEY(id) REFERENCES auth.users (id) ON DELETE CASCADE" in profile_ddl
    assert "chk_profiles_display_name_length" in profile_ddl

    ride_request_ddl = str(CreateTable(RideRequest.__table__).compile(dialect=dialect))
    assert "CREATE TABLE ride_requests" in ride_request_ddl
    assert (
        "FOREIGN KEY(user_id) REFERENCES profiles (id) ON DELETE CASCADE"
        in ride_request_ddl
    )
    assert "geography(POINT,4326)" in ride_request_ddl
    assert "chk_ride_requests_distinct_endpoints" in ride_request_ddl
    assert "chk_ride_requests_departure_window" in ride_request_ddl


def test_alembic_upgrade_sql_generation() -> None:
    """Verify that Alembic generates the complete transactional upgrade SQL."""
    backend_dir = Path(__file__).resolve().parent.parent.parent

    cmd = [
        sys.executable,
        "-m",
        "alembic",
        "upgrade",
        "head",
        "--sql",
    ]
    result = subprocess.run(
        cmd,
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    sql = result.stdout
    assert "CREATE EXTENSION IF NOT EXISTS postgis;" in sql
    assert "CREATE TABLE profiles" in sql
    assert "CREATE TABLE ride_requests" in sql
    assert "idx_ride_requests_pickup_gist" in sql
    assert "idx_ride_requests_destination_gist" in sql
    assert "idx_ride_requests_active_departure" in sql
    assert "idx_ride_requests_active_expiry" in sql
    assert "COMMIT;" in sql


def test_alembic_downgrade_sql_generation() -> None:
    """Verify that Alembic generates the rollback downgrade SQL."""
    backend_dir = Path(__file__).resolve().parent.parent.parent

    cmd = [
        sys.executable,
        "-m",
        "alembic",
        "downgrade",
        "5b69062ab3ef:base",
        "--sql",
    ]
    result = subprocess.run(
        cmd,
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    sql = result.stdout
    assert "DROP INDEX idx_ride_requests_active_expiry;" in sql
    assert "DROP INDEX idx_ride_requests_active_departure;" in sql
    assert "DROP INDEX idx_ride_requests_pickup_gist;" in sql
    assert "DROP TABLE ride_requests;" in sql
    assert "DROP TABLE profiles;" in sql
    assert "COMMIT;" in sql
