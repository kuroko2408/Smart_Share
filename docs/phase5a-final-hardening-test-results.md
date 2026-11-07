# Smart Share — Phase 5A Final Verification & Hardening Test Results

**Project:** Smart Share — Intelligent Cab-Pooling Platform  
**Target Geography:** Mumbai, India  
**Phase:** Phase 5A — Road Distance Normalization, Multi-Waypoint Routing & Route Geometry  
**Stage:** Final Hardening Test Execution Record  
**Date:** November 7, 2026  
**Environment:** Linux (x86_64), Python 3.14.9, Node.js 20+, Supabase PostgreSQL 17 + PostGIS 3.3.7  
**Overall Status:** **100% PASSED**

---

## 1. Test Execution Commands & Raw Summaries

### 1.1 Backend Full Test Suite (Sandboxed & Unsandboxed Live PostGIS)

#### Command: Sandboxed (Mocked Provider & In-Memory Spatial Geometry)
```bash
backend/.venv/bin/pytest backend/app/tests
```
**Output:**
```
============================= test session starts ==============================
platform linux -- Python 3.14.9, pytest-9.2.0, pluggy-1.7.0
rootdir: /home/asta/Projects/Smart_Share/backend
configfile: pyproject.toml
plugins: anyio-4.16.0, asyncio-1.4.1.post1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collecting ... collected 134 items

backend/app/tests/test_api_v1.py ...........................             [ 20%]
backend/app/tests/test_app.py ......                                     [ 24%]
backend/app/tests/test_auth.py ..................                        [ 38%]
backend/app/tests/test_config.py ......                                  [ 42%]
backend/app/tests/test_health.py ..                                      [ 44%]
backend/app/tests/test_matching_algorithms.py ...................        [ 58%]
backend/app/tests/test_matching_phase5a.py .................             [ 70%]
backend/app/tests/test_matching_postgis.py s                             [ 71%]
backend/app/tests/test_models.py ........                                [ 77%]
backend/app/tests/test_routing_normalization.py ......                   [ 82%]
backend/app/tests/test_routing_providers.py ...........                  [ 90%]
backend/app/tests/test_schema.py ......                                  [ 94%]
backend/app/tests/test_spatial.py .......                                [100%]

======================= 133 passed, 1 skipped in 10.12s ========================
```
*Note on skipped test:* `test_matching_postgis.py` is marked with `@pytest.mark.skipif(not os.getenv("SUPABASE_DB_URL") or sandbox_isolated)` so that tests run without external network permissions skip this test cleanly rather than erroring.

#### Command: Live Database Test (Unsandboxed / Network Enabled)
```bash
backend/.venv/bin/pytest backend/app/tests/test_matching_postgis.py
```
**Output:**
```
============================= test session starts ==============================
platform linux -- Python 3.14.9, pytest-9.2.0, pluggy-1.7.0
rootdir: /home/asta/Projects/Smart_Share/backend
configfile: pyproject.toml
plugins: anyio-4.16.0, asyncio-1.4.1.post1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collecting ... collected 1 item

backend/app/tests/test_matching_postgis.py .                             [100%]

============================== 1 passed in 0.74s ===============================
```

#### Command: Full Backend Suite with Live DB (Unsandboxed)
```bash
backend/.venv/bin/pytest backend/app/tests
```
**Output:**
```
============================= test session starts ==============================
platform linux -- Python 3.14.9, pytest-9.2.0, pluggy-1.7.0
rootdir: /home/asta/Projects/Smart_Share/backend
configfile: pyproject.toml
plugins: anyio-4.16.0, asyncio-1.4.1.post1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collecting ... collected 134 items

backend/app/tests/test_api_v1.py ...........................             [ 20%]
backend/app/tests/test_app.py ......                                     [ 24%]
backend/app/tests/test_auth.py ..................                        [ 38%]
backend/app/tests/test_config.py ......                                  [ 42%]
backend/app/tests/test_health.py ..                                      [ 44%]
backend/app/tests/test_matching_algorithms.py ...................        [ 58%]
backend/app/tests/test_matching_phase5a.py .................             [ 70%]
backend/app/tests/test_matching_postgis.py .                             [ 71%]
backend/app/tests/test_models.py ........                                [ 77%]
backend/app/tests/test_routing_normalization.py ......                   [ 82%]
backend/app/tests/test_routing_providers.py ...........                  [ 90%]
backend/app/tests/test_schema.py ......                                  [ 94%]
backend/app/tests/test_spatial.py .......                                [100%]

============================= 134 passed in 13.81s =============================
```

---

### 1.2 Backend Linter & Formatter (Ruff)

#### Command: Lint & Formatting Check
```bash
backend/.venv/bin/ruff check backend && backend/.venv/bin/ruff format --check backend
```
**Output:**
```
All checks passed!
67 files already formatted
```

---

### 1.3 Frontend Automated Test Suite (Vitest)

#### Command:
```bash
cd frontend && npm test -- --run
```
**Output:**
```
 RUN  v4.1.12 /home/asta/Projects/Smart_Share/frontend

 ✓ src/services/__tests__/auth_and_profile.test.ts (3 tests) 9ms
 ✓ src/components/__tests__/smoke.test.tsx (1 test) 3ms
 ✓ src/services/__tests__/ride_requests.test.ts (5 tests) 10ms
 ✓ src/lib/__tests__/env.test.ts (2 tests) 3ms
 ✓ src/services/__tests__/health.test.ts (3 tests) 12ms
 ✓ src/features/home/__tests__/HomePage.test.tsx (4 tests) 240ms
 ✓ src/features/ride-requests/__tests__/RideRequests.test.tsx (12 tests) 373ms

 Test Files  7 passed (7)
      Tests  30 passed (30)
   Start at  21:37:55
   Duration  1.49s (transform 328ms, setup 408ms, import 738ms, tests 651ms, environment 4.60s)
```

---

### 1.4 Frontend Linter (Oxlint)

#### Command:
```bash
cd frontend && npm run lint
```
**Output:**
```
> smart-share-frontend@0.0.0 lint
> oxlint src

Found 0 warnings and 0 errors.
Finished in 12ms on 34 files with 96 rules using 12 threads.
```

---

### 1.5 Frontend TypeScript Compiler (`tsc`)

#### Command:
```bash
cd frontend && npm run typecheck
```
**Output:**
```
> smart-share-frontend@0.0.0 typecheck
> tsc --noEmit -p tsconfig.app.json
```
*(Clean output; 0 errors)*

---

### 1.6 Frontend Production Build (Vite)

#### Command:
```bash
cd frontend && npm run build
```
**Output:**
```
> smart-share-frontend@0.0.0 build
> tsc -b && vite build

vite v8.3.5 building client environment for production...
transforming (2122) src/index.css✓ 2122 modules transformed.
rendering chunks (1)...computing gzip size...
dist/index.html                   0.46 kB │ gzip:   0.29 kB
dist/assets/index-PoplyN4B.css   29.69 kB │ gzip:   6.21 kB
dist/assets/index-CLh3QoGN.js   416.79 kB │ gzip: 124.41 kB

✓ built in 237ms
```

---

## 2. Inventory of New Tests Added in Final Hardening

### 2.1 Final Route API Invariant Revalidation & Promotion (Task 1)
File: `backend/app/tests/test_matching_phase5a.py`

| Test Name | Verification Focus | Result |
|---|---|---|
| `test_route_api_revalidation_accepts_when_within_detour_limits` | Continuous Route API legs keep both detours $\le 15\text{ min}$; proposal geometry attached, detours updated, proposal accepted. | **PASS** |
| `test_route_api_revalidation_rejects_when_passenger_a_exceeds_detour` | Route API introduces detour for Passenger A exceeding `max_extra_minutes` (32 min pooled vs 15 min direct > 15 min limit); `enrich_proposal_geometry` returns `None`. | **PASS** |
| `test_route_api_revalidation_rejects_when_passenger_b_exceeds_detour` | Route API introduces detour for Passenger B exceeding `max_extra_minutes`; `enrich_proposal_geometry` returns `None`. | **PASS** |
| `test_route_api_revalidation_promotes_next_candidate_if_top1_rejected` | Candidate #1 has 18 min detour (exceeds 15 min limit) and Candidate #2 has 8 min detour; `run_matching()` rejects Cand #1 upon Route API revalidation and promotes Cand #2 as Top 1 proposal with geometry attached. | **PASS** |
| `test_route_api_revalidation_handles_differing_route_and_matrix_durations` | Route API continuous duration is longer than matrix estimate (33 min vs 30 min) but detours remain within tolerance; updates proposal with Route API metrics and accepts. | **PASS** |

### 2.2 Passenger Journey Metrics Exact Math Across All 4 Permutations (Task 2)
File: `backend/app/tests/test_matching_phase5a.py`

| Test Name | Verification Focus | Result |
|---|---|---|
| `test_passenger_journey_metrics_all_four_permutations_exact_math` | Uses asymmetric leg durations ($10\text{m}, 20\text{m}, 15\text{m}$) and distances ($5\text{km}, 10\text{km}, 8\text{km}$) across all 4 permutations (`PA_PB_DA_DB`, `PA_PB_DB_DA`, `PB_PA_DA_DB`, `PB_PA_DB_DA`); verifies Passenger A and B pooled duration and distance sum strictly the consecutive legs between their own pickup and dropoff. | **PASS** |

### 2.3 Stale Proposal Lifecycle & Recomputation Safety (Task 3)
File: `backend/app/tests/test_matching_phase5a.py`

| Test Name | Verification Focus | Result |
|---|---|---|
| `test_proposal_detail_candidate_destination_edited_still_valid` | Candidate edits destination within valid spatial threshold; `get_proposal_detail` re-evaluates detour and returns updated proposal with HTTP 200. | **PASS** |
| `test_proposal_detail_candidate_pickup_edited_out_of_range` | Candidate edits pickup > 1.5 km away; `get_proposal_detail` returns HTTP 404 ("Proposal not found or no longer valid."). | **PASS** |
| `test_proposal_detail_target_cancelled` | Target user cancels their ride request; `get_proposal_detail` returns HTTP 404 ("Target ride request is no longer active."). | **PASS** |
| `test_proposal_detail_candidate_cancelled` | Candidate user cancels their ride request; `get_proposal_detail` returns HTTP 404 ("Proposal not found or no longer valid."). | **PASS** |
| `test_proposal_detail_candidate_expired` | Candidate ride request reaches EXPIRED state; `get_proposal_detail` returns HTTP 404 ("Proposal not found or no longer valid."). | **PASS** |
| `test_proposal_detail_candidate_infeasible_detour` | Request tolerance reduced such that detour exceeds limit; `get_proposal_detail` returns HTTP 404. | **PASS** |
| `test_proposal_detail_valid_proposal_enriched_on_demand` | Proposal #2 (initially without geometry per DEC-001) is requested via `get_proposal_detail`; enriched on-demand with Route API geometry and returned with HTTP 200. | **PASS** |

### 2.4 Provider Adapter Robustness & Degradation (Task 4)
File: `backend/app/tests/test_routing_providers.py`

| Test Name | Verification Focus | Result |
|---|---|---|
| `test_ors_provider_directions_geojson_successful_parsing` | Validates OpenRouteService (ORS) Directions API response parsing: Bearer auth header, GeoJSON `[lon, lat]` extraction, leg distances and durations, stop labels. | **PASS** |
| `test_osrm_table_api_timeout_triggers_fallback` | Simulates `httpx.TimeoutException` during OSRM Table API call; engine catches exception, logs warning, and completes detour evaluation via tortuosity fallback with `is_route_approximate = True`. | **PASS** |
| `test_osrm_table_api_http_429_triggers_fallback` | Simulates HTTP 429 Too Many Requests response; engine catches `HTTPStatusError` and completes evaluation via tortuosity fallback. | **PASS** |
| `test_osrm_table_api_invalid_payload_triggers_fallback` | Simulates invalid non-JSON payload from provider; engine catches `JSONDecodeError` and degrades safely to tortuosity fallback. | **PASS** |
| `test_osrm_table_api_none_values_triggers_fallback` | Provider returns duration matrix containing `None` or `null` entries; engine detects missing durations and replaces them with geodesic estimates. | **PASS** |

---

## 3. Database Connectivity & PostGIS Result

- **Target Database:** Supabase-hosted PostgreSQL 17.6 with PostGIS 3.3.7 extension.
- **Migration Schema Version:** `5b69062ab3ef` (clean, zero schema drift).
- **Execution Output:** `backend/app/tests/test_matching_postgis.py` passed in 0.74s.
- **Query Functionality Tested:**
  - Candidate discovery filtering using `ST_DWithin` with geography casts.
  - Spatial indexing on `pickup_location` and `destination_location`.
  - Pairwise departure window overlap querying.
  - Exclusion of identical user requests (`user_id != target_user_id`).

---

## 4. Code Quality & Build Metrics

| Tool / Check | Scope | Violations / Errors | Status |
|---|---|---|---|
| **Ruff Check** | `backend/` (67 files) | 0 errors | **PASS** |
| **Ruff Format** | `backend/` (67 files) | All formatted | **PASS** |
| **Pytest** | `backend/app/tests` (134 items) | 0 failed, 134 passed | **PASS** |
| **Oxlint** | `frontend/src` (34 files) | 0 errors, 0 warnings | **PASS** |
| **Vitest** | `frontend/src` (7 files, 30 tests) | 0 failed, 30 passed | **PASS** |
| **TSC** | `frontend/tsconfig.app.json` | 0 type errors | **PASS** |
| **Vite Build** | `frontend` production bundle | 0 errors, gzip 124 kB | **PASS** |

---

## 5. Conclusion

All tasks specified in the Phase 5A Final Verification and Hardening scope have been completely validated with deterministic automated tests. The implementation preserves all approved architectural decisions (DEC-001, DEC-002, DEC-003) and exhibits zero regressions across backend and frontend codebases.
