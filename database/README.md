# Smart Share — Database Guide (PostgreSQL + PostGIS)

This directory contains the database setup, spatial verification, initialization scripts, and safe management tools for **Smart Share — Intelligent, Location-Based Cab Pooling**.

---

## 1. Overview & Spatial Architecture

Smart Share utilizes **PostgreSQL 16** with the **PostGIS 3.4** spatial extension:
- **Spatial Data Types**: Points represent passenger pickup locations and destinations using standard WGS 84 (`SRID=4326`).
- **Spatial Storage**: `geography(POINT, 4326)` for accurate geodetic calculations on the Earth's spheroid without planar projection distortion.
- **Indexing**: Spatial GiST indexes for efficient nearest-neighbor searches (`<->`) and proximity filtering (`ST_DWithin`).
- **Coordinate Order Convention**: Longitude first ($X$), Latitude second ($Y$). Example: Mumbai is `(72.8777, 19.0760)`.

---

## 2. Option A: Local Development Database (Docker)

A dedicated [`docker-compose.yml`](file:///home/asta/Projects/Smart_Share/docker-compose.yml) is provided in the repository root.

### Port Allocation
- **Host Port**: `5433` (maps to container port `5432`).
- *Rationale*: Avoids port collisions with any existing PostgreSQL service already running on standard port `5432`.

### Quick Start

```bash
# 1. Start the PostGIS database container
docker compose up -d

# 2. Verify that PostgreSQL and PostGIS are healthy
python database/verify_postgis.py
```

### Connection Details (Local)
| Parameter | Value |
|---|---|
| **Host** | `127.0.0.1` |
| **Port** | `5433` |
| **User** | `postgres` |
| **Password** | `postgres` |
| **Database** | `smart_share` |
| **SQLAlchemy Async URL** | `postgresql+asyncpg://postgres:postgres@localhost:5433/smart_share` |
| **Sync / CLI URL** | `postgresql://postgres:postgres@localhost:5433/smart_share` |

---

## 3. Option B: Hosted Development Database (Supabase)

Supabase provides hosted PostgreSQL with PostGIS pre-installed.

### Step 1: Create a Supabase Project
1. Log in to [Supabase](https://supabase.com) and create a project (e.g. `smart-share-dev`).
2. Note your database password and reference ID.

### Step 2: Enable PostGIS
PostGIS is available in Supabase by default, but the extension must be activated:
1. Open your Supabase project dashboard.
2. Go to **Database** -> **Extensions** -> Search for `postgis` -> Toggle **ON**.
3. *Alternative (SQL Editor)*:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   ```

### Step 3: Retrieve Connection String
In Supabase: **Project Settings** -> **Database** -> **Connection string** -> Select **URI**:
- Direct connection (Port `5432`):
  ```text
  postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
  ```
- Or Pooler connection (Port `6543`, prepared statements disabled):
  ```text
  postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?prepared_statement_cache_size=0
  ```

---

## 4. Verifying PostGIS Functionality

Run the included verification script:

```bash
# Verify against local Docker instance (default):
backend/.venv/bin/python database/verify_postgis.py

# Verify against Supabase or custom URL:
backend/.venv/bin/python database/verify_postgis.py --url "postgresql://user:pass@host:5432/dbname"
```

The script executes:
```sql
SELECT version();

SELECT PostGIS_Version();

SELECT ST_AsText(
    ST_SetSRID(
        ST_MakePoint(72.8777, 19.0760),
        4326
    )::geography
);
```

### Verified Output
```text
[1/3] PostgreSQL Version:
      PostgreSQL 16.4 (Debian 16.4-1.pgdg110+2) on x86_64-pc-linux-gnu

[2/3] PostGIS Version:
      3.4 USE_GEOS=1 USE_PROJ=1 USE_STATS=1

[3/3] Spatial Point Construction (Mumbai 72.8777°E, 19.0760°N):
      POINT(72.8777 19.076)
```

---

## 5. Safe Development Database Reset

To reset the local development database cleanly without touching other databases or services:

```bash
# Interactive reset (prompts for confirmation):
./database/reset_dev_db.sh

# Non-interactive reset (automation / CI):
./database/reset_dev_db.sh --force
```

### Safety Guards Built into `reset_dev_db.sh`:
1. **Target Guard**: Strictly limited to database `smart_share`. It will reject any other target.
2. **Environment Guard**: Automatically rejects connections containing `prod`, `production`, or `supabase.co`.
3. **Clean Session Termination**: Closes active backend connections before executing drop/create.
4. **Re-provisions Extensions**: Immediately re-executes [`init_db.sql`](file:///home/asta/Projects/Smart_Share/database/init_db.sql) to re-enable `postgis` and `uuid-ossp`.

---

## 6. Alembic Migration Readiness

The backend's Alembic configuration is linked to the database via `DATABASE_URL`:

```bash
cd backend

# Inspect migration status on the database:
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/smart_share" alembic current

# Run migrations:
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/smart_share" alembic upgrade head
```

---

## 7. Instructions for the Second Developer

To reproduce this exact environment on another workstation:

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd Smart_Share
   ```

2. **Start the local database**:
   ```bash
   docker compose up -d
   ```

3. **Configure the backend environment**:
   ```bash
   cd backend
   cp .env.example .env
   ```
   In `backend/.env`, set:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/smart_share
   ```

4. **Verify the database**:
   ```bash
   source .venv/bin/activate
   python ../database/verify_postgis.py
   ```

5. **Run backend tests**:
   ```bash
   pytest
   ```
