# Smart Share — Phase 5A Final Verification & Hardening Report

**Project:** Smart Share — Intelligent Cab-Pooling Platform  
**Target Geography:** Mumbai, India  
**Phase:** Phase 5A — Road Distance Normalization, Multi-Waypoint Routing & Route Geometry  
**Stage:** Final Verification & Hardening Audit  
**Author:** Senior Full-Stack, Database, QA & Technical Auditor  
**Date:** November 7, 2026  
**Final Verdict:** **PASS (Ready for Phase 5B Authorization)**

---

## 1. Executive Summary

Following the initial implementation of Phase 5A, a focused verification and hardening pass was conducted to audit three critical correctness properties and strengthen provider failure resilience:

1. **Final Route API Feasibility Revalidation (Critical):** Ensured that continuous turn-by-turn route leg durations are used to strictly re-verify that neither passenger's detour exceeds their stated `max_extra_minutes`. If Candidate #1 exceeds tolerance under continuous routing, Candidate #2 is promoted.
2. **Passenger Journey Metrics Math Across All 4 Permutations:** Certified that passenger pooled distance and duration sum strictly the contiguous route legs between that passenger's pickup and dropoff ($PA \to DA$ or $PB \to DB$), rather than full vehicle trajectory totals.
3. **On-Demand Proposal Freshness & Lifecycle Safety:** Certified that `get_proposal_detail` reconstructs proposals dynamically against live database state, safely rejecting cancelled, expired, modified out-of-bounds, or newly infeasible proposals with HTTP 404.
4. **Provider Adapter Robustness & Graceful Degradation:** Verified successful GeoJSON parsing for OpenRouteService (ORS) multi-waypoint directions and deterministic fallback to calibrated geodesic/tortuosity estimates when matrix endpoints encounter timeouts, HTTP 429 rate limits, invalid JSON, or null matrix cells.
5. **Live PostGIS Verification:** Verified spatial candidate discovery against the live Supabase PostgreSQL 17 + PostGIS 3.3.7 database.
6. **Regression Verification:** Full backend test suite (134 passed), frontend test suite (30 passed), linters (Ruff, Oxlint), TypeScript typecheck, and Vite production build passed with zero errors.

---

## 2. Findings from Critical Correctness Audits

### 2.1 Audit 1: Final Route API Feasibility Revalidation (Critical)

#### Finding & Problem Statement
In Stage 1 matrix screening, candidate filtering uses pairwise duration matrix lookups ($t_{AB} + t_{BC} + t_{CD}$). However, when the winning sequence is sent to an external continuous Route API (e.g. OSRM `route/v1` or ORS `v2/directions`), real-world road networks may impose turn restrictions, traffic penalties, or one-way link loops that make the actual multi-waypoint continuous journey longer than the sum of isolated matrix pairs.

Prior to hardening, the engine attached the Route API geometry and leg metrics to the proposal without revalidating whether the newly computed passenger detours still satisfied:
$$\text{final\_pooled\_duration}_i - \text{solo\_direct\_duration}_i \le \text{max\_extra\_minutes}_i$$

#### Hardening Implemented
1. **Per-Leg Invariant Revalidation:** In `enrich_proposal_geometry()`, the engine parses the continuous route legs, calculates exact passenger pooled durations between pickup and dropoff, recomputes each passenger's detour in minutes, and evaluates the tolerance check.
2. **Rejection & Promotion Logic:**
   - If either passenger's detour exceeds their tolerance (`target_max_extra_minutes` or `candidate_max_extra_minutes`), `enrich_proposal_geometry()` returns `None`.
   - In `run_matching()`, if the Top 1 candidate is rejected upon Route API revalidation, the engine iterates to the next ranked candidate in the matrix evaluation list and promotes it to Top 1, ensuring the user receives a strictly valid proposal.
   - In `get_proposal_detail()`, if an on-demand enrichment fails Route API revalidation, the endpoint raises `HTTPException(status_code=404, detail="Proposal not found or no longer valid.")`.

---

### 2.2 Audit 2: Passenger Journey Distance & Duration Correctness Across All 4 Permutations

#### Permutation Walkthrough
A cab-pooling route consists of 4 stops (2 pickups, 2 dropoffs) forming 3 legs (Leg 0, Leg 1, Leg 2). Precedence requires $PA \prec DA$ and $PB \prec DB$. The 4 valid permutations and their exact leg assignments are:

| Permutation Label | Stop Sequence | Passenger A ($PA \to DA$) Legs | Passenger B ($PB \to DB$) Legs |
|---|---|---|---|
| `PA_PB_DA_DB` | $PA \to PB \to DA \to DB$ | Leg 0 + Leg 1 ($PA \to PB + PB \to DA$) | Leg 1 + Leg 2 ($PB \to DA + DA \to DB$) |
| `PA_PB_DB_DA` | $PA \to PB \to DB \to DA$ | Leg 0 + Leg 1 + Leg 2 ($PA \to PB + PB \to DB + DB \to DA$) | Leg 1 ($PB \to DB$) *(detour = 0.0 min)* |
| `PB_PA_DA_DB` | $PB \to PA \to DA \to DB$ | Leg 1 ($PA \to DA$) *(detour = 0.0 min)* | Leg 0 + Leg 1 + Leg 2 ($PB \to PA + PA \to DA + DA \to DB$) |
| `PB_PA_DB_DA` | $PB \to PA \to DB \to DA$ | Leg 1 + Leg 2 ($PA \to DB + DB \to DA$) | Leg 0 + Leg 1 ($PB \to PA + PA \to DB$) |

#### Verification
Deterministic unit test `test_passenger_journey_metrics_all_four_permutations_exact_math` assigned distinct, asymmetric durations and distances to Legs 0, 1, and 2 ($10\text{ min} / 5\text{ km}$, $20\text{ min} / 10\text{ km}$, $15\text{ min} / 8\text{ km}$) and confirmed exact summation for each passenger across all 4 permutations. Neither passenger was billed or assessed for legs occurring before their pickup or after their dropoff.

---

### 2.3 Audit 3: Stale Proposal Lifecycle & Recomputation Safety

#### Finding & Verification
When a user views proposals on the UI, proposals without precomputed geometry (candidates ranked 2 through $N$, per DEC-001) invoke `GET /api/v1/matches/{proposal_id}?request_id={target_id}` for on-demand enrichment.

We audited `get_proposal_detail` to verify handling of lifecycle mutations between initial matching and detail lookup:
1. **Target Request Cancelled/Expired:** Returns HTTP 404 ("Target ride request is no longer active").
2. **Candidate Request Cancelled/Expired:** Re-querying the database detects `status != PENDING`, returns HTTP 404 ("Proposal not found or no longer valid").
3. **Candidate Pickup/Destination Modified:**
   - If candidate coordinates move beyond spatial bounds (1.5 km pickup, 3.0 km destination), returns HTTP 404.
   - If candidate coordinates move within bounds, detour and route metrics are recomputed with updated coordinates.
4. **Tolerance Reduced / Infeasible Detour:**
   - If candidate or target reduces `max_extra_minutes` such that detour exceeds limits, returns HTTP 404.
5. **Route API Infeasible on On-Demand Enrichment:** If continuous route leg durations exceed tolerance upon on-demand enrichment, returns HTTP 404.

All 7 lifecycle test cases passed with zero regressions.

---

## 3. Provider Adapter Robustness & Failure Behavior

### 3.1 OpenRouteService (ORS) Directions API Integration
Added unit test `test_ors_provider_directions_geojson_successful_parsing` validating:
- Proper HTTP headers (`Authorization: Bearer <key>`, `Content-Type: application/json`).
- GeoJSON coordinate order parsing `[lon, lat]` converted to RouteWaypoint `lat, lon`.
- Multi-waypoint continuous geometry LineString extraction.
- Extraction of per-leg distances, durations, and stop labels.

### 3.2 Matrix Stage Resilience (OSRM & ORS Table API)
Deterministic tests verify that the matching engine gracefully absorbs provider disruptions during Stage 1 matrix screening:
- **Connection Timeout (`httpx.TimeoutException`):** Caught, logs warning, falls back to calibrated Mumbai tortuosity matrix ($1.35 \times \text{haversine}$ at $25\text{ km/h}$). Flags `is_route_approximate = True`, `distance_source = DistanceSource.ESTIMATED_HAVERSINE`.
- **HTTP 429 Rate Limit (`httpx.HTTPStatusError`):** Caught, logs warning, falls back to tortuosity matrix without crashing.
- **Malformed / Invalid JSON (`json.JSONDecodeError`):** Caught, falls back safely to tortuosity matrix.
- **Provider Null / None Matrix Values:** Null cells in provider distance/duration tables are detected and replaced with calibrated geodesic estimates.

### 3.3 Route Geometry Stage Fallback
If the external Route API fails during final geometry enrichment:
- `enrich_proposal_geometry()` catches the exception.
- Synthesizes a valid GeoJSON LineString connecting the 4 waypoints directly.
- Marks `is_route_approximate = True`, `distance_is_approximate = True`, and `routing_accuracy = "matrix_duration_synthesized_geometry"`.
- Prevents 500 Internal Server Errors on the matching endpoints.

---

## 4. Summary of Files Changed

| File Path | Changes Made | Exact Reason |
|---|---|---|
| `backend/app/core/config.py` | Added `"backend/.env"` to `model_config.env_file` | Allows tests and commands executed from project root to discover `.env` settings seamlessly without requiring directory changes. |
| `backend/app/matching/service.py` | 1. Added `target_max_extra_minutes: int = 15` to `MatchProposal`.<br>2. Updated `enrich_proposal_geometry` to revalidate invariant `final_pooled - solo <= max_extra_minutes`, updating detours and returning `None` if infeasible.<br>3. Updated `run_matching` with Top 1 rejection promotion loop. | Critical correctness: prevents passengers from receiving proposals that violate stated detour tolerances under continuous Route API routing; promotes next valid candidate. |
| `backend/app/api/v1/endpoints/matching.py` | Added 404 rejection if on-demand `enrich_proposal_geometry` returns `None`. | Correctness: rejects proposals whose continuous route detour violates passenger limits when fetched on-demand. |
| `backend/app/tests/test_matching_phase5a.py` | Added 13 new deterministic unit & integration tests covering Task 1 (invariants & candidate promotion), Task 2 (exact 4-permutation math), and Task 3 (lifecycle freshness & mutations). | Verification requirement: provides deterministic proof of algorithmic and lifecycle correctness. |
| `backend/app/tests/test_routing_providers.py` | Added 5 new tests covering ORS directions parsing, OSRM timeout, HTTP 429, invalid payload, and null matrix handling. | Verification requirement: proves provider adapter robustness and graceful degradation. |

---

## 5. Architectural Decisions Compliance

| Decision Code | Approved Principle | Implementation Status |
|---|---|---|
| **DEC-001** | Top 1 initial geometry enrichment; other proposals enriched on-demand. | **STRICTLY PRESERVED.** Candidate #1 is enriched during `run_matching()`. If rejected on revalidation, Candidate #2 is enriched. Candidates 2..N are returned without geometry until on-demand detail lookup. |
| **DEC-002** | PostGIS discovery limit 20; external routing cap 3. | **STRICTLY PRESERVED.** Up to 20 candidate rows fetched via PostGIS; external routing evaluates at most top 3 candidates. |
| **DEC-003** | Detour feasibility is strictly time-based; distance detour is informational. | **STRICTLY PRESERVED.** Candidate filtering and Route API revalidation gate exclusively on `detour_duration_minutes <= max_extra_minutes`. Distance detour is reported for user information only. |

---

## 6. Live PostGIS Database Verification

A live database test was executed against Supabase PostgreSQL:
- **PostgreSQL Version:** 17.6 (Ubuntu 17.6-1.pgdg24.04+1)
- **PostGIS Extension:** 3.3.7
- **Database Schema Revision:** `5b69062ab3ef`
- **Result:** Candidate discovery query executed cleanly using `ST_DWithin` on `geography(Point, 4326)` columns (`test_matching_postgis.py` passed in 0.74s).

---

## 7. Verification Evidence & Quality Metrics

```
============================= test session starts ==============================
collected 134 items

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

- **Backend Pytest:** 134 passed, 0 failed, 0 errors.
- **Backend Lint & Format (Ruff):** All checks passed; 67 files formatted.
- **Frontend Vitest:** 30 passed, 0 failed across 7 test files.
- **Frontend Lint (Oxlint):** 0 warnings, 0 errors across 34 files.
- **Frontend TypeScript (`tsc --noEmit`):** 0 type errors.
- **Frontend Production Build (`vite build`):** Built cleanly in 237ms.

---

## 8. Phase 5B Readiness Assessment & Verdict

### Readiness Assessment
- The routing abstraction layer is decoupled, robust, and unit-tested.
- Distance and duration models are normalized across all sources (`DistanceSource`, `MultiWaypointRoute`, `RouteLegMetrics`).
- Continuous-route feasibility invariant enforcement guarantees that no match proposal exceeds either passenger's stated detour tolerance.
- Candidate promotion ensures optimal match delivery even when the top matrix candidate encounters road-network route inflation.
- Stale proposal lifecycle edge cases are handled safely with clear HTTP 404 semantics.
- All Phase 1–4 capabilities remain completely intact with zero regressions.
- No database migrations or destructive operations were performed; database remains at clean revision `5b69062ab3ef`.

### Final Verdict
# **PASS**

The Phase 5A routing and distance normalization system is verified, hardened, and ready for **Phase 5B (Fare Estimation Models)** implementation.
