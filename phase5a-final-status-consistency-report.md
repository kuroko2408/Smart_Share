# Smart Share — Phase 5A Final Status Consistency & Edge-Case Audit Report

**Project:** Smart Share — Intelligent Cab-Pooling Platform  
**Target Geography:** Mumbai, India  
**Phase:** Phase 5A — Road Distance Normalization, Multi-Waypoint Routing & Route Geometry  
**Stage:** Final Status Consistency & Edge-Case Verification  
**Author:** Senior Full-Stack, Database, QA & Technical Auditor  
**Date:** November 7, 2026  
**Final Status:** **PASS (Formally Ready for Phase 5B Authorization)**

---

## 1. Executive Summary

This verification pass was initiated to address an apparent discrepancy noted in the review:
- Earlier matching architecture documentation specifies that matchable candidate requests are `ACTIVE`.
- The prior Phase 5A hardening report narrative colloquially referenced candidate requests being rejected when `status != PENDING`.

We conducted an exhaustive audit of the actual models, migrations, SQL queries, endpoints, and test suites. We confirmed that **`ACTIVE` is the sole, authoritative, and implemented lifecycle status for matchable ride requests**. The term `PENDING` never existed in the database schema, Alembic migrations, SQLAlchemy models, or application code; its appearance in the previous summary was purely an inadvertent phrasing in the report's text narrative.

Furthermore, we implemented and verified all four requested edge-case tests plus non-matchable state validations (`MATCHED` and `COMPLETED`). All 140 backend tests and 30 frontend tests pass with zero regressions.

---

## 2. Ride Request Status Consistency Audit

### 2.1 Codebase & Database Inspection

| Component | File Inspected | Implemented Contract |
|---|---|---|
| **SQLAlchemy Model** | [`backend/app/models/ride_request.py`](file:///home/asta/Projects/Smart_Share/backend/app/models/ride_request.py#L28-L36) | `class RideRequestStatus(enum.StrEnum):`<br>`ACTIVE = "ACTIVE"`<br>`MATCHED = "MATCHED"`<br>`CANCELLED = "CANCELLED"`<br>`EXPIRED = "EXPIRED"`<br>`COMPLETED = "COMPLETED"` |
| **Alembic Migration** | [`backend/alembic/versions/2026_11_05_5b69062ab3ef_create_profiles_and_ride_requests.py`](file:///home/asta/Projects/Smart_Share/backend/alembic/versions/2026_11_05_5b69062ab3ef_create_profiles_and_ride_requests.py#L173-L174) | Database CHECK constraint `chk_ride_requests_status` enforces:<br>`status IN ('ACTIVE', 'MATCHED', 'CANCELLED', 'EXPIRED', 'COMPLETED')`.<br>Partial indexes at lines 215, 223, 232, 237 enforce `postgresql_where=sa.text("status = 'ACTIVE'")`. |
| **Candidate Discovery Query** | [`backend/app/matching/candidate_discovery.py`](file:///home/asta/Projects/Smart_Share/backend/app/matching/candidate_discovery.py#L42-L52) | Raw PostGIS SQL query explicitly filters:<br>`WHERE b.status = 'ACTIVE'`<br>`AND b.departure_latest > NOW()`<br>`AND (b.expires_at IS NULL OR b.expires_at > NOW())` |
| **Endpoint Active Verification** | [`backend/app/api/v1/endpoints/matching.py`](file:///home/asta/Projects/Smart_Share/backend/app/api/v1/endpoints/matching.py#L83-L87) | `_get_active_owned_request()` enforces:<br>`if request.status != RideRequestStatus.ACTIVE or effective_expiry <= now:`<br>`raise HTTPException(400, "Ride request is not active or has expired.")` |
| **Service Layer** | [`backend/app/services/ride_request_service.py`](file:///home/asta/Projects/Smart_Share/backend/app/services/ride_request_service.py#L110) | New requests are inserted with `status = RideRequestStatus.ACTIVE.value`. |
| **API Architecture Contract** | [`docs/04-database-api-contracts.md`](file:///home/asta/Projects/Smart_Share/docs/04-database-api-contracts.md#L173-L179) | Approved canonical request statuses: `ACTIVE`, `MATCHED`, `CANCELLED`, `EXPIRED`, `COMPLETED`. |

### 2.2 Discrepancy Resolution
1. **Source of `PENDING`:** A thorough repository search revealed that `PENDING` appears only in early documentation headers (e.g. `Status: Proposed — Pending Review`) and profile onboarding notes. It does not exist in any enum, schema, migration, or database column. Its appearance in the previous session's summary text was an informal narrative slip describing an "open/unmatched" candidate.
2. **Authoritative Status:** `ACTIVE` is the definitive, valid status for matchable ride requests.
3. **Lifecycle State Behavior:**
   - **`ACTIVE`**: Candidate is matchable, discovered by PostGIS, and accepted by all matching endpoints.
   - **`CANCELLED`**: Non-matchable. Excluded by candidate discovery query (`WHERE b.status = 'ACTIVE'`); rejected with HTTP 400 if target request, and HTTP 404 if candidate in `get_proposal_detail`.
   - **`EXPIRED`**: Non-matchable. Excluded by candidate discovery query (`WHERE b.departure_latest > NOW() AND expires_at > NOW()`); rejected with HTTP 400 if target request, and HTTP 404 if candidate in `get_proposal_detail`.
   - **`MATCHED`**: Non-matchable. Excluded by candidate discovery query (`WHERE b.status = 'ACTIVE'`); proposal lookup returns HTTP 404.
   - **`COMPLETED`**: Non-matchable. Excluded by candidate discovery query (`WHERE b.status = 'ACTIVE'`); proposal lookup returns HTTP 404.

---

## 3. Spatial & Freshness Threshold Confirmation

We confirmed the spatial thresholds defined across the architecture and codebase:

| Threshold Parameter | Value | Location in Codebase | Purpose & Rule |
|---|---|---|---|
| **Pickup Radius ($D_{\text{pickup, max}}$)** | `2,000 meters` | [`backend/app/matching/candidate_discovery.py:18`](file:///home/asta/Projects/Smart_Share/backend/app/matching/candidate_discovery.py#L18)<br>[`backend/app/matching/geometry.py:9`](file:///home/asta/Projects/Smart_Share/backend/app/matching/geometry.py#L9) | PostGIS `ST_DWithin` spatial indexing filter for candidate pickup points. |
| **Destination Bypass ($D_{\text{dest, bypass}}$)** | `3,000 meters` | [`backend/app/matching/geometry.py:12`](file:///home/asta/Projects/Smart_Share/backend/app/matching/geometry.py#L12) | Corridor rule: when heading delta is between $45^\circ < \Delta\theta \le 90^\circ$, destination distance must be $\le 3,000\text{ m}$. If $> 3,000\text{ m}$, candidate is pruned in Stage 2. |
| **Max Destination Radius ($D_{\text{dest, max}}$)** | `5,000 meters` | [`backend/app/matching/geometry.py:10`](file:///home/asta/Projects/Smart_Share/backend/app/matching/geometry.py#L10) | Hard cap on destination separation for directional compatibility. |
| **Directional Heading Angle ($\Delta\theta_{\max}$)** | `90.0 degrees` | [`backend/app/matching/geometry.py:11`](file:///home/asta/Projects/Smart_Share/backend/app/matching/geometry.py#L11) | Angles $> 90^\circ$ represent anti-parallel travel and are hard rejected. |

**Confirmation:** No matching eligibility thresholds were modified or weakened.

---

## 4. Additional Edge-Case Implementations & Results

Six targeted tests were implemented in [`backend/app/tests/test_matching_phase5a.py`](file:///home/asta/Projects/Smart_Share/backend/app/tests/test_matching_phase5a.py):

### 4.1 Edge Case 1: Candidate Destination Moves Beyond 3 km Threshold
- **Test:** `test_proposal_detail_candidate_destination_moved_beyond_threshold`
- **Scenario:** Candidate moves destination to Navi Mumbai ($\Delta\theta = 56.8^\circ > 45^\circ$, $D_{\text{dest}} = 9,500\text{ m} > 3,000\text{ m}$).
- **Result:** `is_directionally_compatible` returns `False`; candidate is pruned in Stage 2; `get_proposal_detail` returns HTTP 404 ("Proposal not found or no longer valid."). **(PASS)**

### 4.2 Edge Case 2: Target Request Expires Before Enrichment
- **Test:** `test_proposal_detail_target_expired_before_enrichment`
- **Scenario:** Target request has `departure_latest` in the past before on-demand enrichment is invoked.
- **Result:** `_get_active_owned_request` detects `effective_expiry <= now` and returns HTTP 400 ("Ride request is not active or has expired."). **(PASS)**

### 4.3 Edge Case 3: All 3 Externally Routed Candidates Fail Route API Revalidation
- **Test:** `test_all_three_externally_routed_candidates_fail_route_api_returns_empty`
- **Scenario:** 3 candidates pass Stage 1 and Stage 2. When evaluated with continuous Route API legs, all 3 produce continuous travel times that exceed stated detour tolerance.
- **Result:** Candidate 1 is evaluated and rejected; Candidate 2 is evaluated and rejected; Candidate 3 is evaluated and rejected. `run_matching()` returns empty list `[]`. Route API was called exactly 3 times. `GET /ride-requests/{id}/matches` returns `total_proposals: 0`. **(PASS)**

### 4.4 Edge Case 4: Candidate Promotion Never Exceeds External Routing Cap of Three
- **Test:** `test_candidate_promotion_never_exceeds_external_routing_cap_of_three`
- **Scenario:** 5 directionally compatible candidates are available in Stage 1/2. Provider is configured with `max_routed_candidates = 3` (DEC-002). All 3 routed candidates fail continuous route revalidation.
- **Result:** `routed_candidates` is strictly capped at 3 (`feasible_candidates[:3]`). Candidates 4 and 5 are never evaluated by Route API. Total Route API invocations is exactly 3 (`route_call_count == 3`). `run_matching()` returns `[]`. **(PASS)**

### 4.5 Non-Matchable States: MATCHED and COMPLETED
- **Tests:** `test_proposal_detail_candidate_matched_returns_404`, `test_proposal_detail_candidate_completed_returns_404`
- **Scenario:** Candidate request enters `MATCHED` or `COMPLETED` state in database.
- **Result:** PostGIS candidate discovery query (`WHERE b.status = 'ACTIVE'`) excludes non-ACTIVE requests; proposal lookup raises HTTP 404. **(PASS)**

---

## 5. Summary of Files Changed

| File Path | Description of Changes |
|---|---|
| [`backend/app/tests/test_matching_phase5a.py`](file:///home/asta/Projects/Smart_Share/backend/app/tests/test_matching_phase5a.py) | Added 6 new deterministic edge-case tests: `test_proposal_detail_target_expired_before_enrichment`, `test_proposal_detail_candidate_destination_moved_beyond_threshold`, `test_proposal_detail_candidate_matched_returns_404`, `test_proposal_detail_candidate_completed_returns_404`, `test_all_three_externally_routed_candidates_fail_route_api_returns_empty`, and `test_candidate_promotion_never_exceeds_external_routing_cap_of_three`. |

---

## 6. Regression Verification Summary

```
============================= test session starts ==============================
collected 140 items

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

- **Backend Pytest:** 140 passed, 0 failed across all 13 test modules (including live PostGIS test against Supabase PostgreSQL 17 + PostGIS 3.3.7).
- **Backend Ruff Check & Format:** All checks passed; 67 files formatted.
- **Frontend Vitest:** 30 passed, 0 failed across 7 test suites.
- **Frontend Oxlint:** 0 warnings, 0 errors across 34 files.
- **Frontend TypeScript (`tsc --noEmit`):** 0 type errors.
- **Frontend Production Build (`vite build`):** Clean build in 242ms.

---

## 7. Remaining Limitations & Boundaries

1. **Pairwise Scope:** Pairwise matching is certified; multi-party trip chaining or group pooling (>2 requests) is deferred to future milestones.
2. **Database Migrations:** Database remains cleanly at revision `5b69062ab3ef`; no migration was created or needed.
3. **External Routing Rate Limits:** DEC-001 (single Top 1 enrichment) and DEC-002 (cap of 3 routed candidates) protect external routing quotas. Candidate promotion respects the cap of 3.

---

## 8. Final Verdict

# **PASS**

Status consistency is verified, edge-case resilience is confirmed, and all approved constraints are strictly honored. The codebase is clean, tested, and ready for **Phase 5B (Fare Estimation Models)** authorization.
