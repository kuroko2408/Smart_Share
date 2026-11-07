# Smart Share — Phase 5A Final Status Consistency & Edge-Case Test Results

**Project:** Smart Share — Intelligent Cab-Pooling Platform  
**Target Geography:** Mumbai, India  
**Phase:** Phase 5A — Road Distance Normalization, Multi-Waypoint Routing & Route Geometry  
**Stage:** Final Status Consistency & Edge-Case Test Execution Record  
**Date:** November 7, 2026  
**Environment:** Linux (x86_64), Python 3.14.9, Node.js 20+, Supabase PostgreSQL 17 + PostGIS 3.3.7  
**Overall Status:** **100% PASSED**

---

## 1. Test Execution Commands & Raw Summaries

### 1.1 Backend Full Test Suite (Sandboxed & Unsandboxed Live PostGIS)

#### Command: Sandboxed Full Suite
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
collecting ... collected 140 items

backend/app/tests/test_api_v1.py ...........................             [ 19%]
backend/app/tests/test_app.py ......                                     [ 23%]
backend/app/tests/test_auth.py ..................                        [ 36%]
backend/app/tests/test_config.py ......                                  [ 40%]
backend/app/tests/test_health.py ..                                      [ 42%]
backend/app/tests/test_matching_algorithms.py ...................        [ 55%]
backend/app/tests/test_matching_phase5a.py .......................       [ 72%]
backend/app/tests/test_matching_postgis.py s                             [ 72%]
backend/app/tests/test_models.py ........                                [ 78%]
backend/app/tests/test_routing_normalization.py ......                   [ 82%]
backend/app/tests/test_routing_providers.py ...........                  [ 90%]
backend/app/tests/test_schema.py ......                                  [ 95%]
backend/app/tests/test_spatial.py .......                                [100%]

======================= 139 passed, 1 skipped in 10.13s ========================
```
*Note on skipped test:* `test_matching_postgis.py` is safely skipped inside isolated sandbox environments without network access.

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

============================== 1 passed in 0.76s ===============================
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
collecting ... collected 140 items

backend/app/tests/test_api_v1.py ...........................             [ 19%]
backend/app/tests/test_app.py ......                                     [ 23%]
backend/app/tests/test_auth.py ..................                        [ 36%]
backend/app/tests/test_config.py ......                                  [ 40%]
backend/app/tests/test_health.py ..                                      [ 42%]
backend/app/tests/test_matching_algorithms.py ...................        [ 55%]
backend/app/tests/test_matching_phase5a.py .......................       [ 72%]
backend/app/tests/test_matching_postgis.py .                             [ 72%]
backend/app/tests/test_models.py ........                                [ 78%]
backend/app/tests/test_routing_normalization.py ......                   [ 82%]
backend/app/tests/test_routing_providers.py ...........                  [ 90%]
backend/app/tests/test_schema.py ......                                  [ 95%]
backend/app/tests/test_spatial.py .......                                [100%]

============================= 140 passed in 15.16s =============================
```

---

### 1.2 Backend Linter & Formatter (Ruff)

#### Command:
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

 ✓ src/components/__tests__/smoke.test.tsx (1 test) 5ms
 ✓ src/lib/__tests__/env.test.ts (2 tests) 2ms
 ✓ src/services/__tests__/health.test.ts (3 tests) 10ms
 ✓ src/services/__tests__/auth_and_profile.test.ts (3 tests) 14ms
 ✓ src/services/__tests__/ride_requests.test.ts (5 tests) 10ms
 ✓ src/features/home/__tests__/HomePage.test.tsx (4 tests) 220ms
 ✓ src/features/ride-requests/__tests__/RideRequests.test.tsx (12 tests) 322ms

 Test Files  7 passed (7)
      Tests  30 passed (30)
   Start at  21:48:32
   Duration  1.48s (transform 344ms, setup 420ms, import 780ms, tests 584ms, environment 4.64s)
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
Finished in 11ms on 34 files with 96 rules using 12 threads.
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

✓ built in 242ms
```

---

## 2. Listing of New Tests Added

File: `backend/app/tests/test_matching_phase5a.py`

| Test Name | Focus & Invariant Verified | Outcome |
|---|---|---|
| `test_proposal_detail_target_expired_before_enrichment` | Verifies that if target request has `departure_latest` (or `expires_at`) in the past before on-demand enrichment, endpoint returns HTTP 400 with `"Ride request is not active or has expired."` | **PASS** |
| `test_proposal_detail_candidate_destination_moved_beyond_threshold` | Verifies that when a candidate's destination is moved such that heading delta $\Delta\theta > 45^\circ$ ($56.8^\circ$) and $D_{\text{dest}} > 3,000\text{ m}$ ($9,500\text{ m}$), Stage 2 directional filtering prunes the candidate and returns HTTP 404 (`"Proposal not found or no longer valid."`). | **PASS** |
| `test_proposal_detail_candidate_matched_returns_404` | Verifies that a candidate with status `MATCHED` is excluded by the database candidate discovery query (`WHERE b.status = 'ACTIVE'`) and returns HTTP 404 upon proposal detail retrieval. | **PASS** |
| `test_proposal_detail_candidate_completed_returns_404` | Verifies that a candidate with status `COMPLETED` is excluded by the database query (`WHERE b.status = 'ACTIVE'`) and returns HTTP 404 upon proposal detail retrieval. | **PASS** |
| `test_all_three_externally_routed_candidates_fail_route_api_returns_empty` | Verifies that if all 3 externally routed candidates produce excessive detour in continuous Route API legs, all 3 are rejected, `run_matching()` returns empty proposals list `[]`, and Route API was called exactly 3 times. | **PASS** |
| `test_candidate_promotion_never_exceeds_external_routing_cap_of_three` | Verifies that when 5 candidates are discovered and all routed candidates fail continuous route revalidation, external Route API is called exactly 3 times (DEC-002), candidates 4 & 5 are never routed, and `run_matching()` returns `[]`. | **PASS** |

---

## 3. Database Connectivity & PostGIS Result

- **Target Database:** Supabase PostgreSQL 17.6 with PostGIS 3.3.7 extension.
- **Migration Schema Version:** `5b69062ab3ef` (clean).
- **Execution Output:** `backend/app/tests/test_matching_postgis.py` passed in 0.76s.
- **Database Status Consistency Confirmed:**
  - Table `ride_requests` has CHECK constraint `chk_ride_requests_status` allowing `('ACTIVE', 'MATCHED', 'CANCELLED', 'EXPIRED', 'COMPLETED')`.
  - Partial indexes `idx_ride_requests_active_dep_range`, `idx_ride_requests_active_expiry`, `idx_ride_requests_active_pickup_geog`, `idx_ride_requests_active_dest_geog` explicitly index `status = 'ACTIVE'`.
  - PostGIS discovery query evaluates only rows with `status = 'ACTIVE'`.

---

## 4. Code Quality & Build Metrics

| Check | Scope | Violations | Status |
|---|---|---|---|
| **Ruff Check** | `backend/` (67 files) | 0 errors | **PASS** |
| **Ruff Format** | `backend/` (67 files) | 67 files formatted | **PASS** |
| **Pytest** | `backend/app/tests` (140 tests) | 0 failed, 140 passed | **PASS** |
| **Oxlint** | `frontend/src` (34 files) | 0 errors, 0 warnings | **PASS** |
| **Vitest** | `frontend/src` (7 files, 30 tests) | 0 failed, 30 passed | **PASS** |
| **TSC** | `frontend/tsconfig.app.json` | 0 type errors | **PASS** |
| **Vite Build** | `frontend` production bundle | 0 errors, gzip 124 kB | **PASS** |

---

## 5. Summary Conclusion

All requested status consistency investigations and edge-case verifications have completed with 100% test pass rates. `ACTIVE` is confirmed as the definitive matchable state across all layers. The routing system is hardened, validated, and ready for Phase 5B authorization.
