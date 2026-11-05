#!/usr/bin/env python3
"""Smart Share — PostGIS Verification Script.

Executes required verification queries to confirm PostgreSQL and PostGIS availability.
"""

import argparse
import os
import sys
from pathlib import Path


def load_env_url() -> str | None:
    """Attempt to read DATABASE_URL from environment or backend/.env file."""
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")

    # Check backend/.env
    repo_root = Path(__file__).resolve().parent.parent
    backend_env = repo_root / "backend" / ".env"
    if backend_env.is_file():
        for line in backend_env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val

    # Default fallback for local docker dev
    return "postgresql://postgres:postgres@127.0.0.1:5433/smart_share"


def run_verification(database_url: str) -> bool:
    """Run verification queries against the target database."""
    # Normalize URL for standard psycopg/asyncpg connection
    clean_url = database_url
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://"):
        if clean_url.startswith(prefix):
            clean_url = clean_url.replace(prefix, "postgresql://", 1)

    print("=" * 70)
    print(" Smart Share — PostgreSQL & PostGIS Verification")
    print("=" * 70)
    # Mask password for display
    try:
        from urllib.parse import urlparse

        parsed = urlparse(clean_url)
        safe_netloc = parsed.hostname or "localhost"
        if parsed.port:
            safe_netloc += f":{parsed.port}"
        if parsed.username:
            safe_netloc = f"{parsed.username}:***@{safe_netloc}"
        masked_url = f"{parsed.scheme}://{safe_netloc}{parsed.path}"
        print(f"Target Database: {masked_url}")
    except (ValueError, TypeError):
        print("Target Database: [URL masked]")

    print("-" * 70)

    try:
        import psycopg
    except ImportError:
        print("Error: 'psycopg' library is required to run verification.")
        print(
            "Please activate the backend virtual environment: source backend/.venv/bin/activate"
        )
        return False

    try:
        with psycopg.connect(clean_url) as conn, conn.cursor() as cur:
            # 1. PostgreSQL Version
            cur.execute("SELECT version();")
            pg_version = cur.fetchone()[0]
            print(f"[1/3] PostgreSQL Version:\n      {pg_version}\n")

            # 2. PostGIS Version
            cur.execute("SELECT PostGIS_Version();")
            postgis_version = cur.fetchone()[0]
            print(f"[2/3] PostGIS Version:\n      {postgis_version}\n")

            # 3. Spatial Geographic Point Verification
            # Coordinates: Mumbai (longitude: 72.8777, latitude: 19.0760)
            cur.execute("""
                SELECT ST_AsText(
                    ST_SetSRID(
                        ST_MakePoint(72.8777, 19.0760),
                        4326
                    )::geography
                );
            """)
            point_text = cur.fetchone()[0]
            print(
                f"[3/3] Spatial Point Construction (Mumbai 72.8777°E, 19.0760°N):\n      {point_text}\n"
            )

        print("=" * 70)
        print(" SUCCESS: PostGIS spatial functionality is fully verified!")
        print("=" * 70)
        return True

    except (psycopg.Error, OSError) as exc:
        print(f"\n[ERROR] Connection or query failed: {exc}")
        print("\nTroubleshooting tips:")
        print("1. Ensure local PostGIS container is running: docker compose up -d")
        print("2. If using Supabase, verify your connection string and credentials.")
        print(
            "3. Ensure the 'postgis' extension is enabled: CREATE EXTENSION IF NOT EXISTS postgis;"
        )
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Smart Share PostgreSQL & PostGIS setup."
    )
    parser.add_argument(
        "--url",
        dest="url",
        help="Database connection URL (defaults to DATABASE_URL or local dev database)",
        default=None,
    )
    args = parser.parse_args()

    target_url = args.url or load_env_url()
    if not target_url:
        print("No DATABASE_URL found. Please pass --url or set DATABASE_URL.")
        return 1

    success = run_verification(target_url)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
