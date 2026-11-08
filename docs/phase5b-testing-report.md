# Phase 5B Fare Estimation — Testing Report

**Run date:** 2026-11-08  
**Environment:** Repository development environment; no credentials or secrets were emitted.

## Backend

| Command | Result | Time |
|---|---:|---:|
| `./.venv/bin/pytest -q app/tests/test_fares.py app/tests/test_matching_phase5a.py::test_match_discovery_api_includes_viewer_scoped_fare_estimate` (from `backend/`) | 15 passed | 0.13 s |
| `./.venv/bin/pytest -q` (from `backend/`) | 154 passed, 1 skipped | 10.96 s |
| `./.venv/bin/ruff check app` | Passed, no findings | <1 s |
| `./.venv/bin/ruff format app --check` | 69 files already formatted | <1 s |

Coverage added includes all three quantization modes; base-distance and fractional continuous boundaries; day/night surcharge boundaries at 23:59:59, 00:00, 04:59:59, and 05:00 IST; conditional cross-boundary ranges; invalid distance and naive timestamps; fallback provenance and weakest-link accuracy; response privacy; graceful unavailable fare behavior; and a match-discovery-to-fare-estimation API integration test. Existing Phase 4B/5A suite remains present and passed. The one skipped test is retained from the existing suite; no test was removed or disabled.

The integration test exercises the real FastAPI route, matching orchestration, proposal serializer, and fare estimator. Auth principal, database session, candidate query result, and routing provider are injected for deterministic isolation; this is not a hosted end-to-end test.

## Frontend

| Command | Result | Time |
|---|---:|---:|
| `npm test` (from `frontend/`) | 7 files, 30 tests passed | 3.56 s Vitest duration |
| `npm run lint` | Oxlint passed | Part of 5.9 s combined command |
| `npm run typecheck` | TypeScript passed | Part of 5.9 s combined command |
| `npm run build` | Production build passed; 2,122 modules transformed | Part of 5.9 s combined command |

Frontend coverage verifies the matching UI shows estimates, the viewer's solo baseline, accuracy disclosure, and estimate disclaimer in the proposal flow. No static production match data was introduced.

## Security and data safety checks

- Existing matching ownership and verified-auth dependencies were retained; the complete backend suite passed.
- The fare schema contains no contribution, allocation, savings, or co-passenger solo-fare field. The dedicated API integration test checks serialized fare fields for these exclusions.
- Viewer-scoped passenger metrics prevent serializing the other rider's solo direct distance.
- No migration was created; no reset, truncation, destructive SQL, or hosted database write was run.
- Supabase credentials, database URLs, tokens, and account passwords were not output. Environment files were not edited.

## Testing limitation

No live hosted account was used to validate Supabase sign-in, a real JWT through JWKS verification, hosted PostGIS candidate discovery, or browser-to-hosted-API behavior. This evidence is required before converting the conditional verdict to final PASS.

## Hosted verification regression rerun — 2026-11-08

| Command | Result | Time |
|---|---:|---:|
| `./.venv/bin/pytest -q` (from `backend/`) | 154 passed, 1 skipped | 10.91 s |
| `./.venv/bin/pytest -q app/tests/test_auth.py app/tests/test_api_v1.py app/tests/test_matching_phase5a.py app/tests/test_fares.py` (from `backend/`) | 83 passed | 9.35 s |
| `npm test` (from `frontend/`) | 7 files, 30 tests passed | 3.39 s Vitest duration |

The backend and Vite development servers started. Local frontend HTTP returned 200, backend health returned 200, and unauthenticated match discovery returned 401. The hosted read-only PostGIS availability check and parameterized candidate query succeeded; the query returned zero candidates. A repeat count using all candidate eligibility predicates also returned zero. Hosted Alembic revision remained `5b69062ab3ef`. These checks do not replace valid-account end-to-end coverage: no authorized test login or hosted ride request was available. No migration or data write was performed.
