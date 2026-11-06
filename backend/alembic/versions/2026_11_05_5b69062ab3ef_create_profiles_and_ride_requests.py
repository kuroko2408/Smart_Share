"""create_profiles_and_ride_requests

Revision ID: 5b69062ab3ef
Revises: None
Create Date: 2026-11-05 16:28:45.576159+00:00

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b69062ab3ef"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Ensure PostGIS spatial extension is enabled before creating geography columns
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 2. Create profiles table
    op.create_table(
        "profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "display_name",
            sa.String(length=100),
            server_default="",
            nullable=False,
        ),
        sa.Column(
            "avatar_url",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_profiles"),
        sa.CheckConstraint(
            "char_length(display_name) <= 100",
            name="chk_profiles_display_name_length",
        ),
    )

    # 3. Create ride_requests table
    op.create_table(
        "ride_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pickup_location",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeogFromText",
                name="geography",
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "destination",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeogFromText",
                name="geography",
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "pickup_label",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "destination_label",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "departure_earliest",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "departure_latest",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "seats_requested",
            sa.SmallInteger(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "max_extra_minutes",
            sa.SmallInteger(),
            server_default="15",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ride_requests"),
        sa.CheckConstraint(
            "departure_latest >= departure_earliest",
            name="chk_ride_requests_departure_window",
        ),
        sa.CheckConstraint(
            "seats_requested >= 1 AND seats_requested <= 6",
            name="chk_ride_requests_seats",
        ),
        sa.CheckConstraint(
            "max_extra_minutes >= 0 AND max_extra_minutes <= 180",
            name="chk_ride_requests_max_extra_minutes",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'MATCHED', 'CANCELLED', 'EXPIRED', 'COMPLETED')",
            name="chk_ride_requests_status",
        ),
        sa.CheckConstraint(
            "NOT ST_Equals(pickup_location::geometry, destination::geometry)",
            name="chk_ride_requests_distinct_endpoints",
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at <= departure_latest",
            name="chk_ride_requests_expiry_window",
        ),
    )

    # 4. Create Indexes
    # Spatial GiST indexes
    op.create_index(
        "idx_ride_requests_pickup_gist",
        "ride_requests",
        ["pickup_location"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "idx_ride_requests_destination_gist",
        "ride_requests",
        ["destination"],
        unique=False,
        postgresql_using="gist",
    )
    # Foreign key index
    op.create_index(
        "idx_ride_requests_user_id",
        "ride_requests",
        ["user_id"],
        unique=False,
    )
    # Composite partial index for Stage 1 candidate filtering
    op.create_index(
        "idx_ride_requests_active_departure",
        "ride_requests",
        ["status", "departure_earliest", "departure_latest"],
        unique=False,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    # Partial index for background expiry sweeps
    op.create_index(
        "idx_ride_requests_active_expiry",
        "ride_requests",
        ["expires_at"],
        unique=False,
        postgresql_where=sa.text("status = 'ACTIVE' AND expires_at IS NOT NULL"),
    )


def downgrade() -> None:
    # 1. Drop Indexes
    op.drop_index(
        "idx_ride_requests_active_expiry",
        table_name="ride_requests",
        postgresql_where=sa.text("status = 'ACTIVE' AND expires_at IS NOT NULL"),
    )
    op.drop_index(
        "idx_ride_requests_active_departure",
        table_name="ride_requests",
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.drop_index(
        "idx_ride_requests_user_id",
        table_name="ride_requests",
    )
    op.drop_index(
        "idx_ride_requests_destination_gist",
        table_name="ride_requests",
        postgresql_using="gist",
    )
    op.drop_index(
        "idx_ride_requests_pickup_gist",
        table_name="ride_requests",
        postgresql_using="gist",
    )

    # 2. Drop Tables (in reverse foreign-key dependency order)
    op.drop_table("ride_requests")
    op.drop_table("profiles")
