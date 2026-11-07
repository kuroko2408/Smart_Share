# Phase 4B remediation testing report

## Backend timeout diagnosis

The failing test was the pre-existing SQLite-backed `test_unauthenticated_access_rejected` in `app/tests/test_api_v1.py`. It uses an in-memory `sqlite+aiosqlite` engine, creates the schema in async fixtures, then exercises a FastAPI application through `httpx.ASGITransport`. The stall reproduced before the test made an API/auth/database-network call. A minimal `aiosqlite` connection and a minimal Starlette `TestClient` also stalled on the environment’s default asyncio backend (Python 3.14.9); the fixture cleanup already disposed its engine in `finally`. This was an event-loop/runtime compatibility problem in the older test harness, not hosted PostgreSQL connectivity, pooling, authentication, application startup, or a matching query. It affected an existing Phase 2/3 test and predated Phase 4B.

The fix configures pytest-asyncio’s loop factory to use uvloop and configures Starlette `TestClient` instances to use uvloop. Existing assertions and integration tests remain enabled. The backend dev dependencies now declare the required pytest-asyncio hook version and uvloop. The failing test, API suite and complete suite then completed normally.

## Backend test commands and results

Environment: Python 3.14.9, pytest-asyncio 1.4.1.post1, uvloop 0.23.0.

| Command | Result | Elapsed |
|---|---:|---:|
| `backend/.venv/bin/pytest -q --tb=short` | **90 passed, 0 failed, 0 skipped** | 3.76 s pytest time (5.41 s process; final run) |
| `backend/.venv/bin/pytest app/tests/test_matching_algorithms.py app/tests/test_api_v1.py -q --tb=short` | **37 passed** | 1.11 s pytest time (2.54 s process) |
| `backend/.venv/bin/ruff check app` | Passed | <0.1 s |
| `backend/.venv/bin/ruff format --check app` | 59 files formatted | <0.1 s |

The complete backend run includes Phase 2 authentication tests, Phase 3 request lifecycle/API tests and Phase 4B matching tests. Focused API coverage includes missing/invalid IDs, ownership checks, cancelled targets, and unauthenticated access to all three matching routes. The SQLite test database cannot execute the PostGIS candidate query; actual hosted discovery was not demonstrated because the hosted project currently has no active requests and no test account credentials were supplied.

## Frontend test commands and results

Environment: Node 20.20.2 and npm 12.2.2. npm emitted a version compatibility warning because npm 12 declares support for Node 22.22.2+; all invoked frontend commands completed successfully on the installed runtime.

| Command | Result | Elapsed |
|---|---:|---:|
| `npm test -- --reporter=dot` | **7 files, 26 tests passed** | 7.64 s Vitest time (8.62 s process) |
| `npm run lint` | Oxlint passed | Included in combined command |
| `npm run typecheck` | TypeScript passed | Included in combined command |
| `npm run build` | Vite production build passed; 2,122 modules | 2.08 s Vite time |

The combined command `npm run lint && npm run typecheck && npm run build` exited 0. The matching UI test covers initiation, ranked result rendering, route accuracy and explanation. The existing request workflow tests remain in the same full suite.

## Hosted schema and PostGIS evidence

All queries were read-only and ran inside a read-only transaction. Current hosted information: PostgreSQL 17.11, PostGIS present, Alembic revision `5b69062ab3ef`, two ride request rows, zero `ACTIVE` rows. Existing index:

```sql
CREATE INDEX idx_ride_requests_pickup_gist
ON public.ride_requests USING gist (pickup_location)
```

The candidate predicate uses matching `geography` operands: `ST_DWithin(b.pickup_location, ST_GeogFromText(:a_pickup_wkt), :radius_m)`. WKT is built as `POINT(longitude latitude)` from latitude/longitude API fields. A read-only `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` for the actual parameterized query showed:

- Full candidate query: `idx_ride_requests_active_departure` and `pk_profiles`; spatial `ST_DWithin` is a filter; **0.308 ms**, 4 shared buffers hit, 0 read, 0 rows returned.
- Temporal-only comparison: `idx_ride_requests_active_departure`; **0.030 ms**, 1 buffer hit, 0 rows returned.
- Spatial-only comparison: `idx_ride_requests_pickup_gist` via a geography bounding-box index condition plus `ST_DWithin` recheck; **94.774 ms**, 129 buffers hit, 0 read, 2 rows returned.

The candidate query’s temporal B-tree choice is reasonable for a table of only two rows and no active candidates; no index was forced and no index was changed. The spatial-only query demonstrates that the geography predicate is indexable and the existing GiST is usable. The initial spatial-only execution time is not a performance claim. Realistic larger Mumbai distributions could not be loaded into an isolated PostGIS container because Docker socket access was denied, and the hosted database was not modified to synthesize data.

## Routing provider verification

The asynchronous OSRM adapter made a successful real request to the public OSRM table service for BKC to Powai. It returned a road-network duration of **645.1 seconds** and road distance **8,803.9 metres**, marked `is_approximate=false`. The matching proposal distance is still explicitly approximate because its route-sequence aggregation uses the existing geographic estimate. Response notice states OSRM times are not live-traffic predictions. An adapter unit test checks metadata; provider failure tests verify fallback estimates are labeled approximate.

The provider bounds a table call to four points, has a configurable timeout, spaces requests by 1.05 seconds and falls back on HTTP/provider/timeout/incomplete-response failures. The public OSRM demo has no uptime guarantee and is policy-limited; this is suitable for a demonstrator, not production reliability.

## Services and authenticated end-to-end status

FastAPI and Vite were started together and stopped after verification. FastAPI `/api/v1/health` and Vite `/` both returned HTTP 200. The configured frontend API base was `http://localhost:8000/api/v1`; Supabase URL and publishable-key variables were present without printing their values. Supabase project configuration does not contain a user password or authenticated session.

**Not completed:** authenticated UI sign-in, creation/identification of two active requests from different users, frontend-triggered POST, live JWT verification on that request, hosted PostGIS discovery returning a proposal, and rendered candidate explanation. The hosted database has zero active requests, and no development account credentials/session were available. The user’s instruction explicitly says to document the action rather than invent credentials. Required action: the project owner must provision or provide access to two development Supabase users and compatible active requests (or approved authenticated test sessions). No account or application row was created or changed. The backend’s auth and ownership behavior is covered by automated tests, but those tests are not a substitute for the requested hosted E2E.

## Migration status and remaining gaps

No database migration was created or applied; the hosted Alembic revision and existing indexes remain unchanged. Existing environment files were not changed and are ignored by Git. No screenshots were available because the interactive authenticated flow could not be completed.

Remaining acceptance gaps: authenticated hosted frontend-to-backend-to-PostGIS flow; large-volume realistic query-plan study; public demo service reliability. Accordingly, this report does **not** claim full Phase 4B acceptance.
