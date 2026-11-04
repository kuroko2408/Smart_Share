# Smart Share

> **Intelligent, Location-Based Cab Pooling**
>
> *"Same place. Same time. Compatible routes. One smarter shared ride."*

> [!IMPORTANT]
> Smart Share is a **passenger matching and ride-coordination prototype**, not an operational cab-dispatch service. It does not operate a taxi fleet, guarantee vehicle availability, assign drivers, or process payments. These are explicitly out of scope for the current version.

---

## Table of Contents

- [About the Project](#about-the-project)
- [Problem Being Addressed](#problem-being-addressed)
- [Core Idea](#core-idea)
- [Technology Stack](#technology-stack)
- [Architecture Overview](#architecture-overview)
- [Repository Structure](#repository-structure)
- [Documentation](#documentation)
- [Current Development Phase](#current-development-phase)
- [Setup Instructions](#setup-instructions)
- [Branching and Contribution Conventions](#branching-and-contribution-conventions)

---

## About the Project

Smart Share is an intelligent, location-based cab-pooling platform designed to connect passengers who are travelling from the same or nearby pickup locations to compatible destinations within overlapping departure-time windows.

**Team:** Terminal 1
**Hackathon:** NOVEX 2026 — Round 2
**Category:** Smart Automation

---

## Problem Being Addressed

People leaving crowded venues — concerts, college events, railway stations, airports, offices — frequently book separate cabs despite sharing similar routes. The result is:

- Higher individual travel costs.
- Underutilized vehicle seats.
- Unnecessary traffic during peak hours.
- No reliable way to discover compatible co-travellers in real time.

Existing informal solutions (messaging groups, personal contacts) are slow, manual, and do not evaluate route feasibility.

---

## Core Idea

Smart Share performs **journey-feasibility matching** rather than simple proximity grouping:

1. A passenger creates a ride request with a pickup location, destination, departure window, seat count, and maximum acceptable extra travel time.
2. The system filters candidate passengers by pickup proximity and time-window overlap.
3. Compatible combinations are evaluated against route fit, detour limits, and vehicle capacity.
4. A feasible pickup/drop-off sequence is proposed.
5. Fare shares and estimated savings are calculated and presented transparently.
6. Each passenger accepts or declines the proposal.

The matching engine is **deterministic and explainable** — no unvalidated machine learning is used in the MVP.

---

## Technology Stack

| Layer | Technology |
|:---|:---|
| **Frontend** | React · Vite · TypeScript |
| **Styling** | Tailwind CSS |
| **UI Components** | shadcn/ui |
| **Frontend Routing** | React Router |
| **Server State** | TanStack Query |
| **Form Validation** | Zod |
| **Maps** | Leaflet + OpenStreetMap |
| **Backend** | Python · FastAPI |
| **Data Validation** | Pydantic |
| **ORM** | SQLAlchemy 2 |
| **Database Migrations** | Alembic |
| **Database** | PostgreSQL + PostGIS (Supabase) |
| **Authentication** | Supabase Auth |
| **Road Routing** | openrouteservice (replaceable adapter) |
| **Backend Testing** | Pytest |
| **Frontend Testing** | Vitest |
| **End-to-End Testing** | Playwright |
| **Frontend Deployment** | Vercel (or equivalent) |
| **Backend Deployment** | Render (or equivalent) |

---

## Architecture Overview

```
Passenger / Smartphone (Browser)
        │
        ▼
  React + Vite + TypeScript (Frontend)
  ├── Authentication (Supabase Auth)
  ├── Map Interface (Leaflet + OpenStreetMap)
  └── API Communication (TanStack Query)
        │
        ▼
  FastAPI Backend
  ├── Auth Verification (Supabase JWT)
  ├── Ride Request Service
  ├── Geospatial Candidate Filtering (PostGIS)
  ├── Route Compatibility & Matching Engine
  │       ├── Road Route / ETA Evaluation
  │       ├── Detour & Stop-Order Feasibility
  │       └── Fare Estimation
  └── Routing Provider Adapter (openrouteservice)
        │
        ▼
  PostgreSQL + PostGIS (Supabase)
```

The frontend and backend are **independently runnable** services. The backend exposes a versioned REST API (`/api/v1/`). The routing provider sits behind a replaceable adapter so it can be swapped without touching matching logic.

---

## Repository Structure

```
smart-share/
├── frontend/                   # React + Vite + TypeScript application
│   └── src/
│       ├── app/                # Root app setup (router, providers, global layout)
│       ├── components/
│       │   ├── ui/             # Primitive UI components (shadcn/ui wrappers)
│       │   └── shared/         # Reusable composed components
│       ├── features/           # Feature modules (ride request, match, group)
│       ├── hooks/              # Custom React hooks
│       ├── services/           # API client and external service wrappers
│       ├── lib/                # Utility functions and helpers
│       ├── types/              # TypeScript type definitions and interfaces
│       └── assets/             # Static assets (images, icons, fonts)
│
├── backend/                    # Python + FastAPI application
│   └── app/
│       ├── api/v1/endpoints/   # HTTP route handlers
│       ├── core/               # Configuration, settings, and application setup
│       ├── models/             # SQLAlchemy ORM models
│       ├── schemas/            # Pydantic request/response schemas
│       ├── services/           # Business logic layer
│       ├── repositories/       # Database access layer
│       ├── matching/           # Passenger matching engine
│       ├── routing/            # Routing provider adapter
│       ├── fares/              # Fare estimation module
│       └── tests/              # Pytest test suite
│
├── database/
│   ├── migrations/             # Alembic migration scripts
│   └── diagrams/               # ER diagrams and schema diagrams
│
├── docs/
│   ├── 01-project-charter.md
│   ├── 02-srs-prd.md
│   ├── 03-system-architecture-tdd.md
│   ├── 04-database-api-contracts.md
│   ├── 05-roadmap.md
│   ├── 06-developer-guide.md
│   ├── ADR/                    # Architecture Decision Records
│   └── diagrams/               # Architecture and flow diagrams
│
├── .gitignore
└── README.md
```

---

## Documentation

| Document | Description |
|:---|:---|
| [01 — Project Charter](docs/01-project-charter.md) | Project goals, scope, team structure, success criteria |
| [02 — SRS / PRD](docs/02-srs-prd.md) | Functional and non-functional requirements |
| [03 — System Architecture & TDD](docs/03-system-architecture-tdd.md) | Technical architecture, component design, matching engine spec |
| [04 — Database & API Contracts](docs/04-database-api-contracts.md) | Database schema, API endpoint definitions, request/response shapes |
| [05 — Roadmap](docs/05-roadmap.md) | Development phases, milestones, deliverables, completion criteria |
| [06 — Developer Guide](docs/06-developer-guide.md) | Local setup, workflow, testing, branch conventions |
| [ADR/](docs/ADR/) | Architecture Decision Records for significant choices |

---

## Current Development Phase

**Phase 1 — Repository and Development Foundation** *(in progress)*

| Phase | Description | Status |
|:---|:---|:---|
| Phase 0 | Planning and Documentation | ✅ Complete |
| Phase 1 | Repository and Development Foundation | 🔄 In Progress |
| Phase 2 | Backend Core and Database | 🔲 Pending |
| Phase 3 | Matching Engine | 🔲 Pending |
| Phase 4 | Frontend Application | 🔲 Pending |
| Phase 5 | Integration, Testing, and Demo | 🔲 Pending |

---

## Setup Instructions

> [!NOTE]
> This section will be completed as the project is initialized. The instructions below are placeholders and will be updated with verified commands.

### Prerequisites

- Git
- Node.js (recent stable LTS)
- npm
- Python 3.11+ (verify against project dependencies)
- PostgreSQL with PostGIS
- A Supabase project (for hosted database and authentication)
- An openrouteservice API key

### Clone the Repository

```bash
git clone <REPOSITORY_URL>
cd smart-share
```

### Frontend Setup

```bash
cd frontend
cp .env.example .env.local
# Fill in .env.local with your values
npm install
npm run dev
```

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
cp .env.example .env
# Fill in .env with your values
pip install -r requirements.txt
# Run database migrations (Alembic — instructions TBD)
uvicorn app.main:app --reload
```

> [!WARNING]
> `requirements.txt` and `package.json` have not yet been generated. These setup commands will be verified and updated when the frontend and backend are initialized.

---

## Branching and Contribution Conventions

### Branch Strategy

| Branch | Purpose |
|:---|:---|
| `main` | Stable, reviewed code only. Direct commits are not permitted. |
| `dev` | Integration branch for completed features. |
| `feature/<short-name>` | Individual feature development (e.g., `feature/ride-request-api`) |
| `fix/<short-name>` | Bug fixes (e.g., `fix/matching-detour-overflow`) |
| `chore/<short-name>` | Tooling, dependencies, documentation updates |

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

feat(matching): add detour feasibility check
fix(api): correct ride request 422 response schema
chore(deps): update fastapi to 0.115
docs(adr): record routing adapter decision
```

### Pull Requests

- All changes must go through a pull request into `dev` or `main`.
- Both developers should review changes that touch shared interfaces (API contracts, database schema, matching logic).
- API contract changes must be reflected in `docs/04-database-api-contracts.md`.
- Database schema changes must be implemented through Alembic migrations — no manual schema edits.

### Secrets Policy

> [!CAUTION]
> Never commit credentials, API keys, database passwords, JWT secrets, or generated tokens. Use `.env` files locally (which are gitignored) and environment variable configuration for deployment.
> Use `.env.example` files for documenting required variables.

---

*Smart Share — NOVEX 2026 Hackathon Project | Team: Terminal 1*
