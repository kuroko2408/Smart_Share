#!/usr/bin/env bash
# =============================================================================
# Smart Share — Safe Development Database Reset Script
# =============================================================================
# Drops and recreates ONLY the isolated 'smart_share' development database.
#
# Usage:
#   ./database/reset_dev_db.sh [--force]
#
# Environment variables respected:
#   PGHOST (default: 127.0.0.1)
#   PGPORT (default: 5433)
#   PGUSER (default: postgres)
#   PGDATABASE (strictly restricted to 'smart_share' for safety)
# =============================================================================

set -euo pipefail

HOST="${PGHOST:-127.0.0.1}"
PORT="${PGPORT:-5433}"
USER="${PGUSER:-postgres}"
DB_NAME="${PGDATABASE:-smart_share}"

# Safety guard 1: Ensure database name is strictly 'smart_share'
if [[ "${DB_NAME}" != "smart_share" ]]; then
    echo "ERROR: Refusing to reset database '${DB_NAME}'."
    echo "This script is strictly restricted to development database 'smart_share'."
    exit 1
fi

# Safety guard 2: Guard against production hosts
if [[ "${HOST}" =~ (prod|production|supabase.co) ]]; then
    echo "ERROR: Refusing to reset hosted or production database on '${HOST}'."
    echo "Resetting production databases is prohibited."
    exit 1
fi

FORCE=false
for arg in "$@"; do
    if [[ "$arg" == "--force" || "$arg" == "-y" ]]; then
        FORCE=true
    fi
done

if [[ "${FORCE}" != "true" ]]; then
    echo "WARNING: This will drop and recreate the local development database '${DB_NAME}' on ${HOST}:${PORT}."
    echo "All data in '${DB_NAME}' will be permanently deleted."
    read -r -p "Are you sure you want to proceed? (type 'yes' to confirm): " CONFIRM
    if [[ "${CONFIRM}" != "yes" ]]; then
        echo "Aborted."
        exit 0
    fi
fi

echo "--- Resetting development database '${DB_NAME}' on ${HOST}:${PORT} ---"

# Terminate active connections and recreate database using docker exec if container is active,
# or psql if available locally
if docker ps --format '{{.Names}}' | grep -q "^smartshare-db$"; then
    echo "Using Docker container 'smartshare-db'..."
    docker exec smartshare-db psql -U "${USER}" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();" \
        -c "DROP DATABASE IF EXISTS ${DB_NAME};" \
        -c "CREATE DATABASE ${DB_NAME};"
    docker exec smartshare-db psql -U "${USER}" -d "${DB_NAME}" -c "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
elif command -v psql >/dev/null 2>&1; then
    echo "Using local psql..."
    psql -h "${HOST}" -p "${PORT}" -U "${USER}" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();" \
        -c "DROP DATABASE IF EXISTS ${DB_NAME};" \
        -c "CREATE DATABASE ${DB_NAME};"
    psql -h "${HOST}" -p "${PORT}" -U "${USER}" -d "${DB_NAME}" -f "$(dirname "$0")/init_db.sql"
else
    echo "ERROR: Neither docker container 'smartshare-db' nor local 'psql' is available."
    exit 1
fi

echo "--- Re-verifying PostGIS on fresh '${DB_NAME}' ---"
if docker ps --format '{{.Names}}' | grep -q "^smartshare-db$"; then
    docker exec smartshare-db psql -U "${USER}" -d "${DB_NAME}" -c "SELECT version(); SELECT PostGIS_Version();"
fi

echo "--- Development database '${DB_NAME}' reset completed successfully ---"
