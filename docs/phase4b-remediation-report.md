# Phase 4B remediation, integration and acceptance audit

**Final verdict: CONDITIONAL PASS.** The backend timeout is fixed, full automated regressions pass, the real OSRM adapter returned a road-network result, existing hosted schema/indexes were inspected read-only, and both local services started successfully. Full authenticated hosted matching remains unverified because no active hosted requests or test-account session were available. Phase 4B cannot receive PASS until that mandatory workflow is demonstrated.

## Original failure and root cause

The earlier full backend suite timed out in the first existing API integration test, `test_unauthenticated_access_rejected`. That test builds an in-memory SQLite database through `aiosqlite` and invokes the FastAPI app with ASGI transport. The stall reproduced before the test made an API/authentication or hosted database request. The same minimal `aiosqlite` operation and a minimal Starlette `TestClient` stalled on this environment’s default asyncio backend (Python 3.14.9). The test fixture already closed its session/engine. The evidence points to event-loop/runtime compatibility in the test harness, not database connectivity, pooling, auth, application startup, or Phase 4B matching. It affected a pre-existing Phase 2/3 test and therefore predates matching implementation.

The test configuration now uses pytest-asyncio’s uvloop loop factory; Starlette `TestClient` fixtures use uvloop as well. The failing test and all existing API assertions remain enabled. The dev dependency floor now reflects the pytest-asyncio hook used by the fix and explicitly includes uvloop on non-Windows systems. No timeout was increased and no test was skipped or removed.

## Changes implemented

- Added the no-credential OSRM HTTP table provider behind the existing routing abstraction. It uses async HTTP, a configurable timeout/base URL, at most four points per matrix, a process-wide 1.05 second request spacing, response validation, and the existing approximate fallback on provider errors.
- Kept the routing precision distinction explicit: OSRM duration is road-network based, not live traffic-aware; shared stop-sequence distance remains approximate. Fallback duration and distance are geographic approximations and are marked as such.
- A new hard-feasibility test exposed two precedence-valid stop orders that never had both passengers onboard. The engine still enumerates all six precedence-valid orders but rejects those two as non-sharing journeys before calculating a proposal score.
- Added matching API security regression tests for unauthenticated matching routes, invalid request IDs, cross-user access, and cancelled targets.
- Updated algorithm/API, onboarding, implementation and testing documentation.
- No production schema migration or hosted database write was made.

Full file inventory is in [the implementation report](phase4b-implementation-report.md). No files were deleted. The supplied `.env` and `.env.local` were left unchanged and `git check-ignore` confirms both remain ignored.

## Backend and frontend results

- Complete backend: `backend/.venv/bin/pytest -q --tb=short` — **90 passed, 0 failed, 0 skipped**; final run 3.76 seconds reported by pytest, 5.41 seconds process time.
- Phase 3 request/API and model tests: `backend/.venv/bin/pytest app/tests/test_api_v1.py app/tests/test_models.py -q --tb=short` — **34 passed in 1.50 seconds**.
- Phase 2 auth tests: `backend/.venv/bin/pytest app/tests/test_auth.py -q --tb=short` — **18 passed in 0.32 seconds**.
- Matching and API-focused tests: `backend/.venv/bin/pytest app/tests/test_matching_algorithms.py app/tests/test_api_v1.py -q --tb=short` — **34 passed in 1.49 seconds**.
- `backend/.venv/bin/ruff check app` passed; `ruff format --check app` confirmed all 59 files formatted.
- Frontend `npm test -- --reporter=dot` — **7 files, 26 tests passed** in 7.64 seconds Vitest time.
- `npm run lint`, `npm run typecheck`, and `npm run build` all passed. Vite built 2,122 modules; Vite build time was 2.08 seconds.
- npm emitted a Node/npm version compatibility warning (Node 20.20.2 with npm 12.2.2); the test, lint, type check and build commands still exited successfully.

Detailed commands/results are in [the testing report](phase4b-testing-report.md).

## Hosted database and GiST audit

Read-only queries verified PostgreSQL 17.11, PostGIS, Alembic revision `5b69062ab3ef`, two ride request rows, zero active rows, and the existing index:

```sql
CREATE INDEX idx_ride_requests_pickup_gist
ON public.ride_requests USING gist (pickup_location)
```

Candidate SQL applies `ST_DWithin` directly to `geography` using `ST_GeogFromText` on bound WKT. API lat/lon becomes `POINT(lon lat)`. The full candidate `EXPLAIN (ANALYZE, BUFFERS)` used `idx_ride_requests_active_departure` and `pk_profiles`, with `ST_DWithin` as a filter; execution was 0.308 ms with four shared buffers hit and none read. The temporal-only query used the active departure index (0.030 ms). A spatial-only comparison used `idx_ride_requests_pickup_gist` with a geography bounding-box index condition and `ST_DWithin` recheck (94.774 ms, two rows returned). These timings describe the tiny current dataset only. The temporal index is a reasonable planner choice for the full query at two rows and zero active requests; no index was forced or changed.

The spatial predicate is index-compatible and the GiST is usable. Large-volume realistic performance could not be measured because access to the local Docker socket was denied and the hosted database was not altered to seed synthetic data.

## Routing verification

The implemented OSRM adapter successfully queried the public service for BKC to Powai: **645.1 seconds**, **8,803.9 metres**, `is_approximate=false` for its road-network leg result. This demonstrates one real route calculation, not an authenticated matching proposal. In proposal responses, shared distance remains marked approximate. OSRM has no live traffic data, and its public demo is best-effort, for reasonable noncommercial use and policy-limited to no more than one request per second. Provider errors fall back to the clearly labeled 1.40× geodesic / 22 km/h estimate. See the [algorithm and routing documentation](phase4b-matching-algorithm.md).

## Actual service and authenticated E2E audit

FastAPI and the actual Vite frontend were started together and stopped after checks. The backend health endpoint and Vite root both returned HTTP 200. Frontend configuration uses `http://localhost:8000/api/v1`; Supabase URL and publishable-key variables are present. Only configuration presence was reported; no key values were printed.

The authenticated matching path was **not** completed. Current hosted data has zero active requests; the supplied environment provides Supabase project configuration but no user credentials or authenticated browser session. No credentials were invented, no users were created, and no hosted requests were added. Required next action: the project owner must provision/access two development Supabase users and create or identify two compatible active requests (or provide approved authenticated sessions). Then run the actual sign-in, matching POST, JWT validation, hosted PostGIS discovery, and rendered proposal explanation flow. Automated SQLite/API tests do not substitute for this acceptance test.

## Migration and data safety

No migration was created or applied. Current hosted Alembic revision remains `5b69062ab3ef`. No table, index, schema or Supabase-managed authentication record was modified. All hosted inspection was read-only.

## Remaining limitations and final decision

The outstanding acceptance gaps are the real authenticated frontend-to-hosted-PostGIS matching journey and large-volume realistic query-plan measurement. Public OSRM demo uptime is also not guaranteed. Core code and regression checks are complete, but the final end-to-end product criterion cannot be claimed without test-user/request provisioning.

**CONDITIONAL PASS — remediation and local/regression verification complete; hosted authenticated acceptance remains pending owner-provisioned test access and data.** No Phase 5 work was started.
