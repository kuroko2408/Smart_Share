# Smart Share — Operations and Developer Onboarding Guide

**Document:** Operations & Developer Onboarding Guide  
**Version:** 1.0  
**Status:** Initial Draft  
**Project:** Smart Share

---

## 1. Purpose

This guide explains how developers should set up, run, test, maintain and contribute to Smart Share.

It is intended to help both project developers establish a consistent local environment and follow the same development workflow.

The commands and configuration below represent the proposed setup. They must be verified against the actual dependency versions and project files created during implementation.

## 2. Prerequisites

Install the following:

| Tool | Purpose |
|---|---|
| Git | Version control |
| Node.js | Frontend runtime |
| npm | Frontend package management |
| Python | Backend runtime |
| pip | Python package installation |
| PostgreSQL | Database |
| PostGIS | Geospatial extension |
| Code Editor | Development |
| Browser | Frontend testing |

Recommended:

- A recent stable Node.js LTS version.
- A supported Python version compatible with the selected FastAPI dependencies.
- PostgreSQL version supported by the selected PostGIS release.
- Git configured with the developer's identity.

Exact versions should be pinned in project configuration before development begins.

## 3. Repository Structure

Proposed root structure:

```text
smart-share/
├── frontend/
├── backend/
├── database/
│   ├── migrations/
│   ├── seed_demo.sql
│   └── schema-notes.md
├── docs/
│   ├── 01-project-charter.md
│   ├── 02-srs-prd.md
│   ├── 03-system-architecture-tdd.md
│   ├── 04-database-api-contracts.md
│   ├── 05-roadmap.md
│   ├── 06-developer-guide.md
│   ├── ADR/
│   └── diagrams/
├── .gitignore
├── README.md
└── LICENSE
```

The frontend and backend must remain independently runnable.

## 4. Clone the Repository

```bash
git clone <REPOSITORY_URL>
cd smart-share
```

Replace `<REPOSITORY_URL>` with the actual repository URL.

## 5. Frontend Setup

### 5.1 Navigate to Frontend

```bash
cd frontend
```

### 5.2 Install Dependencies

```bash
npm install
```

### 5.3 Environment Variables

Create `.env.local` inside `frontend/`.

Example:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1

VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=

VITE_MAP_TILE_URL=
```

Notes:

- Use the actual Supabase project URL.
- Use the appropriate public/anon key for the frontend.
- Never place a Supabase service-role key in frontend environment variables.
- Map tile configuration depends on the selected provider.
- Do not commit `.env.local`.

### 5.4 Run the Development Server

```bash
npm run dev
```

The Vite development server normally runs at:

```text
http://localhost:5173
```

### 5.5 Build for Production

```bash
npm run build
```

### 5.6 Preview Production Build

```bash
npm run preview
```

The exact available scripts must match `frontend/package.json`.

## 6. Backend Setup

### 6.1 Navigate to Backend

```bash
cd backend
```

### 6.2 Create a Virtual Environment

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 6.3 Install Dependencies

If the backend uses `pyproject.toml`:

```bash
pip install -e ".[dev]"
```

If dependency installation is defined differently, follow the actual backend package configuration.

### 6.4 Environment Variables

Create a local `.env` file inside `backend/`.

Example:

```env
APP_ENV=development
APP_NAME=Smart Share
API_V1_PREFIX=/api/v1

DATABASE_URL=

SUPABASE_URL=
SUPABASE_JWT_SECRET=

ROUTING_PROVIDER=
ROUTING_API_KEY=

CORS_ORIGINS=http://localhost:5173

LOG_LEVEL=INFO
```

Notes:

- Never commit `.env`.
- Never expose database passwords.
- Never expose routing-provider API keys.
- The authentication verification method must match the selected Supabase configuration.
- If asymmetric signing keys/JWKS are used, configure verification accordingly rather than assuming a JWT secret is available.

### 6.5 Run Database Migrations

After configuring the database:

```bash
alembic upgrade head
```

### 6.6 Start the Backend

```bash
uvicorn app.main:app --reload --port 8000
```

The backend should be available at:

```text
http://localhost:8000
```

### 6.7 API Documentation

FastAPI's interactive documentation should be available at:

```text
http://localhost:8000/docs
```

OpenAPI schema:

```text
http://localhost:8000/openapi.json
```

Health endpoint:

```text
http://localhost:8000/health
```

The exact paths depend on the final application configuration.

## 7. Database Setup

### 7.1 Create a PostgreSQL Database

Create a development database using the selected local or hosted PostgreSQL environment.

### 7.2 Enable PostGIS

Run:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

Verify:

```sql
SELECT PostGIS_Version();
```

### 7.3 Configure Connection String

Example format:

```text
postgresql+psycopg://USERNAME:PASSWORD@HOST:5432/DATABASE_NAME
```

Use the driver and connection format supported by the SQLAlchemy configuration.

### 7.4 Apply Migrations

```bash
alembic upgrade head
```

### 7.5 Inspect Migration History

```bash
alembic history
```

### 7.6 Generate a Migration

After changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe_schema_change"
```

Review the generated migration before applying it.

Do not assume autogeneration detects every database-specific change, especially custom indexes, extensions or partial constraints.

## 8. Authentication Setup

Smart Share uses Supabase Auth as the proposed identity provider.

Development process:

1. Create or select the Supabase project.
2. Configure authentication providers.
3. Configure the frontend Supabase URL and public key.
4. Configure backend token verification.
5. Verify protected API endpoints.
6. Test invalid and expired tokens.
7. Test ownership and authorization checks.

The backend must validate the access token on protected endpoints.

Never trust user IDs supplied by the frontend as proof of identity.

## 9. Running the Full Application

Use two terminal sessions.

### Terminal 1 — Backend

```bash
cd smart-share/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Terminal 2 — Frontend

```bash
cd smart-share/frontend
npm run dev
```

Open:

```text
http://localhost:5173
```

Verify:

- Frontend loads.
- Backend health endpoint responds.
- Frontend can communicate with backend.
- Authentication works.
- Database operations succeed.

## 10. Development Workflow

### 10.1 Branch Strategy

Recommended branches:

- `main` — stable code.
- `develop` — integration branch.
- `feature/<name>` — feature development.
- `fix/<name>` — bug fixes.
- `docs/<name>` — documentation updates.

Example:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/ride-request-api
```

### 10.2 Commit Convention

Use descriptive commit prefixes:

| Prefix | Usage |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation |
| `test:` | Tests |
| `refactor:` | Code restructuring |
| `chore:` | Tooling or maintenance |
| `perf:` | Performance improvement |

Examples:

```bash
git commit -m "feat: add ride request creation endpoint"
git commit -m "fix: prevent duplicate group acceptance"
git commit -m "docs: update API contract"
```

### 10.3 Pull Request Rules

Before merging:

- Ensure the code builds.
- Run relevant tests.
- Review authorization.
- Review database changes.
- Update documentation.
- Check that secrets are not committed.
- Request review from the other developer.

Avoid direct commits to `main`.

## 11. API Development Rules

- Use Pydantic request and response schemas.
- Keep route handlers thin.
- Put business logic in service modules.
- Use repository functions for database access where practical.
- Return consistent response structures.
- Use meaningful HTTP status codes.
- Validate resource ownership.
- Document new endpoints.
- Update OpenAPI schemas.
- Test failure cases, not just successful cases.

## 12. Frontend Development Rules

- Use TypeScript.
- Organize code by feature.
- Keep API communication in service modules.
- Use TanStack Query for server state where appropriate.
- Use Zod for client-side validation.
- Handle loading, error and empty states.
- Avoid duplicating backend business logic.
- Never store privileged secrets in frontend code.
- Do not assume a match proposal represents a confirmed vehicle booking.

## 13. Matching Engine Development Rules

- Keep the algorithm independent of FastAPI route handlers.
- Keep thresholds configurable.
- Version the matching algorithm.
- Test every hard constraint.
- Use road-routing data for route feasibility.
- Treat proximity as an initial filter only.
- Recalculate group feasibility after adding a passenger.
- Ensure one request cannot join multiple active groups.
- Log aggregate matching metrics without unnecessary personal information.

## 14. Testing Guide

### 14.1 Backend Tests

Run:

```bash
pytest
```

Run with coverage if configured:

```bash
pytest --cov=app
```

### 14.2 Frontend Tests

Run:

```bash
npm run test
```

The actual script must be configured in `package.json`.

### 14.3 End-to-End Tests

Run:

```bash
npx playwright test
```

### 14.4 Required Test Scenarios

Matching:

- Compatible pickup locations.
- Incompatible pickup locations.
- Overlapping departure windows.
- Non-overlapping departure windows.
- Similar destinations.
- Excessive detour.
- Insufficient capacity.
- Multiple seats requested.
- Expired request.
- Already matched request.

Group lifecycle:

- Successful acceptance.
- Duplicate acceptance.
- Decline.
- Cancellation.
- Proposal expiry.
- Invalid state transition.

Concurrency:

- Two users attempting to reserve the final seat.
- Same request accepted into two groups.
- Acceptance concurrent with cancellation.

External services:

- Routing-provider timeout.
- Invalid routing response.
- Rate limit.
- Temporary provider failure.

## 15. Synthetic Demo Dataset

The project should include a repeatable demo dataset.

Example scenarios:

### Scenario A — Compatible Passengers

- Multiple passengers leave the same venue.
- Departure windows overlap.
- Destinations lie along compatible routes.
- Combined seat requirements fit the configured capacity.

Expected result: a feasible group is proposed.

### Scenario B — Incompatible Time Windows

- Two passengers have similar routes.
- Their departure windows do not overlap.

Expected result: they are not matched.

### Scenario C — Excessive Detour

- Pickup points are nearby.
- Destinations require a significant route deviation.

Expected result: the combination is rejected.

### Scenario D — Capacity Conflict

- Candidate requests require more seats than the group capacity.

Expected result: the group is rejected or the additional request is excluded.

### Scenario E — Concurrent Acceptance

- Two operations attempt to reserve the last available seat.

Expected result: only a valid transaction succeeds; capacity is never exceeded.

The dataset must be reproducible so that the demo can be reset.

## 16. Environment Management

Maintain separate configurations for:

- Local development.
- Testing.
- Staging/demo.
- Production, if applicable.

Do not reuse production credentials in local development.

Suggested environment files:

```text
frontend/
├── .env.example
└── .env.local

backend/
├── .env.example
└── .env
```

Commit only example files with blank or placeholder values.

## 17. Deployment Guide

### 17.1 Frontend

Deploy the frontend using Vercel or an equivalent static/frontend hosting platform.

Configure:

- Build command.
- Output directory.
- API base URL.
- Supabase public configuration.
- Map configuration.

### 17.2 Backend

Deploy FastAPI using Render or an equivalent service.

Configure:

- Python runtime.
- Dependency installation.
- Application start command.
- Database URL.
- Authentication verification settings.
- Routing-provider credentials.
- CORS origins.
- Logging.

### 17.3 Database

Use Supabase PostgreSQL or the selected PostgreSQL hosting environment.

Before deployment:

- Enable PostGIS.
- Apply migrations.
- Verify constraints and indexes.
- Load demo data if needed.
- Confirm database connectivity.

### 17.4 Production Checklist

- HTTPS enabled.
- Environment variables configured.
- CORS restricted to expected frontend origins.
- Database migrations applied.
- Health endpoint working.
- Authentication verified.
- Secrets protected.
- Routing-provider quotas checked.
- Demo workflow tested.
- No debug configuration exposed.

## 18. Troubleshooting

### Backend Cannot Connect to Database

Check:

- `DATABASE_URL`.
- Database availability.
- Credentials.
- Network access.
- PostgreSQL driver.
- Whether migrations have been applied.

### PostGIS Functions Not Found

Check whether the extension is enabled:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

Verify:

```sql
SELECT PostGIS_Version();
```

### Frontend Cannot Reach Backend

Check:

- Backend process is running.
- API base URL is correct.
- CORS origins are configured.
- Port is correct.
- Browser console and network logs.

### Authentication Fails

Check:

- Supabase URL.
- Public key.
- Access-token validity.
- Backend token verification configuration.
- JWT issuer and audience settings where applicable.
- Authentication provider configuration.

### Routing Requests Fail

Check:

- Provider credentials.
- API quota.
- Request format.
- Provider availability.
- Timeout configuration.

Do not silently substitute straight-line distance for a failed road-routing request.

### Migration Errors

Check:

- Current migration history.
- Database connection.
- Whether the extension exists.
- Whether generated migrations contain valid operations.
- Whether the database schema has drifted.

Never delete migration history or manually modify shared database state without understanding the consequences.

## 19. Security Guidelines

- Never commit `.env` files.
- Never expose database credentials.
- Never expose service-role keys.
- Never log access tokens.
- Validate all backend inputs.
- Enforce authorization server-side.
- Restrict access to user and group data.
- Use HTTPS for deployed environments.
- Protect expensive matching endpoints from abuse.
- Minimize stored location information.
- Review third-party provider terms and data policies.

## 20. Documentation Maintenance

The following rules apply:

- Update SRS when requirements change.
- Update architecture documentation when components or responsibilities change.
- Update database documentation when schema changes.
- Update API contracts when endpoints change.
- Update roadmap as milestones change.
- Update this guide when setup commands or environment variables change.
- Record significant technical decisions as ADRs.

Documentation must describe the current implementation, not an outdated plan.

## 21. New Developer Onboarding Checklist

A developer is considered onboarded when they can:

- [ ] Clone the repository.
- [ ] Install frontend dependencies.
- [ ] Create and activate the backend virtual environment.
- [ ] Configure local environment variables.
- [ ] Connect to the development database.
- [ ] Verify PostGIS.
- [ ] Apply migrations.
- [ ] Start the backend.
- [ ] Start the frontend.
- [ ] Open the API documentation.
- [ ] Authenticate successfully.
- [ ] Run backend tests.
- [ ] Run frontend tests.
- [ ] Understand the matching-engine flow.
- [ ] Understand the database relationships.
- [ ] Create a feature branch.
- [ ] Submit a pull request.

---

**Document Status:** Initial Developer Guide. Update commands, scripts, dependency versions and deployment settings to match the actual repository implementation.