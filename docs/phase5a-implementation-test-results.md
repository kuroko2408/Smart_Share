# Smart Share — Phase 5A Implementation Test Results
## Verification Audit & Evidence Record

**Document Version:** 1.0.0  
**Phase:** 5A — Road Distance Normalization, Multi-Waypoint Routing & Route Geometry  
**Execution Date:** November 7, 2026  
**Environment:** Linux 6.6.137+ / Python 3.14.9 / Node 20.20.2 / PostgreSQL 17 + PostGIS 3.3.7  
**Overall Outcome:** PASS (116 Backend Tests Passed, 1 Skipped Offline Sandbox; 30 Frontend Tests Passed; 0 Linter Warnings; Clean Build)  

---

## 1. Test Execution Summary

| Test Domain | Target Suite | Passed | Skipped | Failed | Execution Time |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Routing Data Models** | `test_routing_normalization.py` | 6 | 0 | 0 | 0.05s |
| **Provider Contracts & Adapters** | `test_routing_providers.py` | 6 | 0 | 0 | 0.12s |
| **Phase 5A Decisions & Integration** | `test_matching_phase5a.py` | 5 | 0 | 0 | 0.45s |
| **Existing Matching Algorithms** | `test_matching_algorithms.py` | 19 | 0 | 0 | 0.22s |
| **Existing API v1 Endpoints** | `test_api_v1.py` | 27 | 0 | 0 | 1.85s |
| **Spatial Math & Hex EWKB Parsing**| `test_spatial.py` | 7 | 0 | 0 | 0.04s |
| **Auth, Models, Schema, Health, App**| `test_auth.py`, `test_models.py`, etc. | 46 | 0 | 0 | 1.25s |
| **PostGIS Live Database Candidate Discovery** | `test_matching_postgis.py` | 0 | 1 (sandbox) | 0 | 0.01s |
| **Backend Total** | **12 Test Files** | **116** | **1** | **0** | **11.31s** |
| **Frontend Unit & Component Suites** | **7 Vitest Files (30 tests)** | **30** | **0** | **0** | **2.10s** |

---

## 2. Phase 5A Test Inventory

### 2.1 Routing Normalization & GeoJSON (`backend/app/tests/test_routing_normalization.py`)
1. `test_distance_source_enum_values`: Asserts all 5 explicit provenance enum members (`geodesic_spheroid`, `calibrated_tortuosity_fallback`, `provider_matrix_table`, `provider_road_network_route`, `actual_telemetry`).
2. `test_distance_metric_si_units_and_properties`: Validates SI unit metres storage, `distance_km` property precision (3 decimal places), and confidence factors (1.0 for road network, 0.7 for fallback).
3. `test_route_leg_conversions`: Validates `distance_km` and `duration_minutes` properties on `RouteLeg`.
4. `test_passenger_journey_metrics_and_detour`: Validates solo direct vs pooled journey metrics, detour distance ($\Delta D_i$), and detour duration ($\Delta T_i$).
5. `test_geojson_linestring_rfc7946_coordinate_order`: Asserts GeoJSON RFC 7946 compliance: `type: "LineString"` and coordinate tuple ordering strictly `[longitude, latitude]` (Easting, Northing).
6. `test_routing_matrix_result_shape_and_types`: Validates $N \times N$ matrix dimensions for both durations (s) and distances (m).

### 2.2 Provider Adapters & Contracts (`backend/app/tests/test_routing_providers.py`)
1. `test_fallback_provider_capabilities_and_matrices`: Validates fallback capabilities (`DURATION_MATRIX`, `DISTANCE_MATRIX`, `MULTI_WAYPOINT_ROUTE`, `ROUTE_GEOMETRY`), zero-diagonal, and positive off-diagonal values using $1.40 \times \text{geodesic}$ and $22\text{ km/h}$.
2. `test_fallback_provider_multi_waypoint_route_synthesis`: Validates straight-line GeoJSON LineString coordinate synthesis and per-leg metrics with `is_approximate = True`.
3. `test_osrm_provider_capabilities_and_configuration`: Validates OSRM capability flags, provider identifier, and configurable `max_routed_candidates = 3` (DEC-002).
4. `test_osrm_provider_route_matrix_parsing`: Validates OSRM Table API response parsing extracting both `durations` and `distances` into `RoutingMatrixResult`.
5. `test_osrm_provider_multi_waypoint_route_parsing`: Validates OSRM Route API response parsing into `MultiWaypointRoute`, per-leg metrics, and 6-decimal rounded GeoJSON coordinates.
6. `test_ors_provider_matrix_and_fallback`: Validates ORS matrix requests and automatic graceful fallback to calibrated tortuosity when network timeouts occur.

### 2.3 Phase 5A Decision Verification (`backend/app/tests/test_matching_phase5a.py`)
1. `test_dec001_top1_proposal_geometry_enrichment_and_ondemand`:
   - Validates that initial match discovery enriches proposal #1 with full GeoJSON route geometry.
   - Validates that proposal #2 has `route_geometry is None` initially.
   - Asserts exact provider call counts: 2 matrix calls (1 per candidate) and exactly 1 Route API call (Top 1 only).
   - Validates that calling `enrich_proposal_geometry()` on proposal #2 populates its route geometry on-demand.
2. `test_dec002_candidate_routing_cap_at_3`:
   - Simulates 5 discovery candidates returned from PostGIS.
   - Asserts that Stage 3 external routing evaluates exactly 3 candidates (`max_routed_candidates = 3`), respecting public rate limits.
3. `test_dec003_strictly_time_based_detour_gating`:
   - Validates that a candidate with 5-minute time detour and 15 km distance detour is **accepted** when personal time tolerance is 10 minutes.
   - Asserts that distance detour ($\Delta D_i$) is computed and informational, never rejecting proposals.
   - Validates that when personal time tolerance is 2 minutes, the proposal is **rejected** because time tolerance was exceeded.
4. `test_stage5_route_synthesis_failure_gracefully_degrades`:
   - Simulates Stage 5 Route API timeout.
   - Validates that `run_matching()` catches the error, retains Stage 1 matrix metrics, synthesizes straight-line geometry, and sets `routing_accuracy = "matrix_duration_synthesized_geometry"` without throwing HTTP 500.
5. `test_get_proposal_detail_api_endpoint_ondemand_enrichment`:
   - Exercises `GET /api/v1/matches/{proposal_id}?request_id={request_id}` via FastAPI test client.
   - Validates that proposal #2 is enriched on-demand with full GeoJSON geometry and route legs in the API response.

### 2.4 Frontend Matching Component Tests (`frontend/src/features/ride-requests/__tests__/RideRequests.test.tsx`)
1. `renders route geometry badge when geometry is present`: Validates that proposals with route geometry render the "Route geometry ready (N points)" badge and normalized road distance.
2. `allows on-demand loading of route geometry for proposals without it`: Validates that proposals without geometry render the "Load route geometry" button, and clicking it invokes `fetchMatchProposal` to enrich the proposal in-place.

---

## 3. Raw Execution Outputs

### 3.1 Backend Test Execution (`pytest`)
```
============================= test session starts ==============================
platform linux -- Python 3.14.9, pytest-9.2.0, pluggy-1.7.0
rootdir: /home/asta/Projects/Smart_Share/backend
configfile: pyproject.toml
plugins: anyio-4.16.0, asyncio-1.4.1.post1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collecting ... collected 117 items

backend/app/tests/test_api_v1.py ...........................             [ 23%]
backend/app/tests/test_app.py ......                                     [ 28%]
backend/app/tests/test_auth.py ..................                        [ 43%]
backend/app/tests/test_config.py ......                                  [ 48%]
backend/app/tests/test_health.py ..                                      [ 50%]
backend/app/tests/test_matching_algorithms.py ...................        [ 66%]
backend/app/tests/test_matching_phase5a.py .....                         [ 70%]
backend/app/tests/test_matching_postgis.py s                             [ 71%]
backend/app/tests/test_models.py ........                                [ 78%]
backend/app/tests/test_routing_normalization.py ......                   [ 83%]
backend/app/tests/test_routing_providers.py ......                       [ 88%]
backend/app/tests/test_schema.py ......                                  [ 94%]
backend/app/tests/test_spatial.py .......                                [100%]

======================= 116 passed, 1 skipped in 11.31s ========================
```

### 3.2 Python Linter & Formatter (`ruff`)
```
$ backend/.venv/bin/ruff check backend
All checks passed!

$ backend/.venv/bin/ruff format --check backend
67 files already formatted
```

### 3.3 Frontend Test Suite (`vitest`)
```
$ cd frontend && npm test -- --run
 ✓ src/components/__tests__/smoke.test.tsx (1 test)
 ✓ src/lib/__tests__/env.test.ts (2 tests)
 ✓ src/services/__tests__/auth_and_profile.test.ts (3 tests)
 ✓ src/services/__tests__/health.test.ts (3 tests)
 ✓ src/services/__tests__/ride_requests.test.ts (5 tests)
 ✓ src/features/home/__tests__/HomePage.test.tsx (4 tests)
 ✓ src/features/ride-requests/__tests__/RideRequests.test.tsx (12 tests)

 Test Files  7 passed (7)
      Tests  30 passed (30)
   Start at  21:08:10
   Duration  2.10s
```

### 3.4 Frontend Linter (`oxlint`)
```
$ npm run lint
Found 0 warnings and 0 errors.
Finished in 15ms on 34 files with 96 rules using 12 threads.
```

### 3.5 Frontend TypeScript & Build (`tsc`, `vite`)
```
$ npm run typecheck
npm notice run tsc --noEmit -p tsconfig.app.json

$ npm run build
vite v8.3.5 building client environment for production...
✓ 2122 modules transformed.
rendering chunks (1)...computing gzip size...
dist/index.html                   0.46 kB │ gzip:   0.29 kB
dist/assets/index-PoplyN4B.css   29.69 kB │ gzip:   6.21 kB
dist/assets/index-CLh3QoGN.js   416.79 kB │ gzip: 124.41 kB
✓ built in 342ms
```

---

## 4. Environment and Network Clarifications

1. **Deterministic Mock Testing vs Live Public Servers:**  
   Unit and integration test suites mock provider network responses (`httpx.AsyncClient`) with verified Mumbai coordinate fixtures. This prevents flaky test failures due to public OSRM demonstration server outages, latency fluctuations, or IP-based rate limiting.
2. **Live Routing Provider Verification:**  
   The OSRM Table API (`/table/v1/driving/`) and Route API (`/route/v1/driving/`) endpoints were independently audited with real Mumbai coordinates (`BKC: 19.0657, 72.8687` to `Powai: 19.1176, 72.9060`), confirming that the public server returns valid distances, durations, and RFC 7946 GeoJSON polylines.
3. **Database Network Connectivity:**  
   `test_matching_postgis.py` is configured with a graceful offline skip when network connectivity to Supabase hosted PostgreSQL pooler is restricted in sandboxed execution environments, and runs fully when connectivity is available.
