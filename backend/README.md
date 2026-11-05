# Smart Share — Backend Service Foundation

Production-conscious FastAPI backend foundation for **Smart Share — Intelligent, Location-Based Cab Pooling**.

---

## 1. Directory Structure

```text
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── __init__.py
│   │       │   └── health.py
│   │       ├── __init__.py
│   │       └── router.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── base.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── health.py
│   ├── services/
│   │   └── __init__.py
│   ├── repositories/
│   │   └── __init__.py
│   ├── matching/
│   │   └── __init__.py
│   ├── routing/
│   │   └── __init__.py
│   ├── fares/
│   │   └── __init__.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_app.py
│   │   ├── test_config.py
│   │   └── test_health.py
│   └── main.py
├── alembic/
│   ├── versions/
│   │   └── .gitkeep
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 2. Technology Stack

- **Python**: `>=3.11`
- **FastAPI**: Modern, high-performance web framework for APIs
- **Uvicorn**: Lightning-fast ASGI web server
- **Pydantic & Pydantic Settings**: Centralized type-safe schema and environment management
- **SQLAlchemy 2**: Modern async ORM foundation
- **GeoAlchemy2 & Shapely**: PostGIS spatial types (`Geography`) and geometric operations
- **Alembic**: Database migrations and schema versioning
- **asyncpg & psycopg**: High-performance PostgreSQL drivers
- **Pytest & Pytest-Asyncio**: Asynchronous and synchronous test suite
- **Ruff**: Extremely fast Python linter and code formatter

---

## 3. Environment Configuration

Copy `.env.example` to `.env` in the `backend/` directory:

```bash
cp .env.example .env
```

### Environment Variables

| Variable | Description | Default | Example |
|---|---|---|---|
| `APP_ENV` | Application environment (`development`, `test`, `production`) | `development` | `development` |
| `APP_NAME` | Name of the service | `Smart Share` | `Smart Share` |
| `API_V1_PREFIX` | Prefix for version 1 API routes | `/api/v1` | `/api/v1` |
| `DATABASE_URL` | PostgreSQL connection string | `""` | `postgresql+asyncpg://user:pass@localhost:5432/smart_share` |
| `SUPABASE_URL` | Supabase project URL | `""` | `https://your-project.supabase.co` |
| `SUPABASE_JWKS_URL` | Supabase JWKS URL for asymmetric JWT verification | `""` | `https://your-project.supabase.co/auth/v1/.well-known/jwks.json` |
| `ROUTING_PROVIDER` | Routing engine identifier | `""` | `openrouteservice` |
| `ROUTING_API_KEY` | Routing engine API key | `""` | `your-routing-key` |
| `CORS_ORIGINS` | Allowed origins (comma-separated or JSON array) | `http://localhost:5173` | `http://localhost:5173,http://localhost:3000` |
| `LOG_LEVEL` | Log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` | `INFO` |

> **Note on Supabase Auth**: The foundation does not assume symmetric JWT verification. Asymmetric JWKS verification (`SUPABASE_JWKS_URL`) is supported to match modern Supabase auth setups.

---

## 4. Local Development

### Prerequisites

- Python 3.11 or later
- Virtual environment (`venv`)

### Installation

From the `backend/` directory:

```bash
# 1. Create a virtual environment
python3 -m venv .venv

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install dependencies with development tooling
pip install -e ".[dev]"
```

### Running the Application

Start the local development server with auto-reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Health check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Interactive OpenAPI docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 5. Health Endpoint

Exposed at `GET /health` (and versioned at `GET /api/v1/health`):

```json
{
  "status": "ok",
  "service": "smart-share-backend"
}
```

---

## 6. Database & Migrations (PostgreSQL + PostGIS)

Smart Share uses PostgreSQL 16 with PostGIS 3.4. See [`../database/README.md`](../database/README.md) for complete local and Supabase setup instructions.

### Starting Local Database

```bash
# From repository root
docker compose up -d

# Verify PostGIS functionality
python ../database/verify_postgis.py
```

### Applying Migrations (Alembic)

When `DATABASE_URL` is configured in your environment or `.env`:

```bash
# Apply migrations to the database
alembic upgrade head

# Create a new migration revision after modifying models
alembic revision --autogenerate -m "describe_migration"

# Check migration history
alembic history
```

If `DATABASE_URL` is unconfigured, Alembic will safely refuse to run and report that credentials are required.

---

## 7. Developer Tooling

### Running Tests

Execute the automated test suite with pytest:

```bash
pytest
```

### Linting and Code Formatting

Check and format code with Ruff:

```bash
# Check code for linting issues
ruff check .

# Automatically apply safe fixes
ruff check --fix .

# Check formatting
ruff format --check .

# Auto-format files
ruff format .
```
