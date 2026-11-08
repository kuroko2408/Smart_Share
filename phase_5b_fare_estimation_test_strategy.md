# Smart Share — Phase 5B Fare Estimation Test Strategy & Verification Plan (Post-Audit Targeted Amendment)

**Project:** Smart Share — Intelligent Cab-Pooling Platform  
**Target Geography:** Mumbai, India  
**Phase:** Phase 5B — Fare Estimation Models  
**Status:** Test Specification (Pending Product Owner Decision Approvals on DEC-004 & DEC-013)  
**Date:** November 8, 2026  
**Related Documents:**
- `docs/phase_5b_fare_estimation_design.md`
- `docs/phase_5b_fare_model_decisions.md`
- `docs/phase_5b_fare_estimation_risk_analysis.md`
- `docs/phase_5b_final_pre_implementation_audit.md`

---

## 1. Overview & Objectives

This document establishes the comprehensive test strategy for Phase 5B (Fare Estimation Models).

The strategy verifies:
1. Statutory compliance with Mumbai taxi tariffs across parameterized quantization modes.
2. Pure mathematical invariants of proportional cost allocation and Hamilton-Hare equivalence.
3. Provenance and accuracy tier handling under the conservative weakest-link rule.
4. Strict viewer-centric API privacy and intentional inferential disclosure boundaries.
5. Exact dual wire format serialization eliminating IEEE 754 floating-point drift.

---

## 2. Test Suites & Scenario Matrix

### 2.1 Suite 1: Pure Unit Tariff & Mathematical Tests
*Target Module:* `backend/app/fares/mumbai.py`

| Test ID | Scenario Description | Inputs | Expected Output | Assertion Type |
| :--- | :--- | :--- | :--- | :--- |
| **TEST-TAR-01** | Zero distance | $d = 0\text{ m}$, Day | Meter: ₹33, Raw: 33.00 | Exact equality |
| **TEST-TAR-02** | Flag drop boundary | $d = 1500\text{ m}$, Day | Meter: ₹33, Raw: 33.00 | Exact equality |
| **TEST-TAR-03** | 1,501m Ceiling Mode | $d = 1501\text{ m}$, CEILING | Meter: ₹35, Pulses: 1 (Sub: 35.19) | Ceiling step |
| **TEST-TAR-04** | 1,501m Floor Mode | $d = 1501\text{ m}$, FLOOR | Meter: ₹33, Pulses: 0 (Sub: 33.00) | Floor step |
| **TEST-TAR-05** | 1,501m Continuous Mode | $d = 1501\text{ m}$, CONTINUOUS | Meter: ₹33, Raw: 33.0219 | Continuous linear |
| **TEST-TAR-06** | 1,600m Slab Boundary | $d = 1600\text{ m}$, all modes | Meter: ₹35, Pulses: 1 (Sub: 35.19) | Full slab completed |
| **TEST-TAR-07** | 1,700m Slab Boundary | $d = 1700\text{ m}$, all modes | Meter: ₹37, Pulses: 2 (Sub: 37.38) | Full slab completed |
| **TEST-TAR-08** | Night boundary: 23:59:59 | $d = 1000\text{ m}$, 23:59:59 IST | Meter: ₹33 (Multiplier: 1.00) | Day tariff |
| **TEST-TAR-09** | Night boundary: 00:00:00 | $d = 1000\text{ m}$, 00:00:00 IST | Meter: ₹41 (Gross: 41.25, Mult: 1.25) | Night tariff |
| **TEST-TAR-10** | Night boundary: 04:59:59 | $d = 1000\text{ m}$, 04:59:59 IST | Meter: ₹41 (Gross: 41.25, Mult: 1.25) | Night tariff |
| **TEST-TAR-11** | Night boundary: 05:00:00 | $d = 1000\text{ m}$, 05:00:00 IST | Meter: ₹33 (Multiplier: 1.00) | Day tariff |
| **TEST-TAR-12** | Night boundary: 05:00:01 | $d = 1000\text{ m}$, 05:00:01 IST | Meter: ₹33 (Multiplier: 1.00) | Day tariff |
| **TEST-TAR-13** | Invalid negative distance | $d = -50.0\text{ m}$ | Raises `InvalidFareInputError` | Exception check |
| **TEST-TAR-14** | Naive datetime rejection | `datetime.now()` (naive) | Raises `InvalidTimezoneError` | Exception check |

---

### 2.2 Suite 2: Cost Allocation & Economic Invariant Tests
*Target Module:* `backend/app/fares/allocator.py`

| Test ID | Scenario Description | Inputs | Expected Output | Assertion Type |
| :--- | :--- | :--- | :--- | :--- |
| **TEST-ALC-01** | Exact Sum Conservation | $F_{\text{shared}} = 223.00, F_A = 188.00, F_B = 143.00$ | $S_A + S_B == 223.00$ | Exact budget balance |
| **TEST-ALC-02** | Largest-Remainder Equivalence | 1,000 randomized fare vectors | All match Hamilton-Hare | `lr_alloc == round_alloc` |
| **TEST-ALC-03** | Percentage Savings Bound | $F_A, F_B \ge 33.00, F_{\text{shared}} \le F_A + F_B$ | $\|\Delta_{\text{pp}}\| \le 0.04\text{ percentage points}$ | Bound assertion |
| **TEST-ALC-04** | Monotonicity (Ceteris Paribus) | $F_B = 150, F_{\text{shared}} = 250, F_A \in [50, 300]$ | $S_A(F_A + 10) \ge S_A(F_A)$ | Non-decreasing share |
| **TEST-ALC-05** | Negative Savings (Dissavings) | $F_{\text{shared}} = 400.00, F_A = 150.00, F_B = 150.00$ | $S_A = 200, \text{savings} = -50$ | `status == "NEGATIVE"` |
| **TEST-ALC-06** | Break-Even Neutrality | $F_{\text{shared}} = 300.00, F_A = 150.00, F_B = 150.00$ | $S_A = 150, \text{savings} = 0.00$ | `status == "BREAK_EVEN"` |
| **TEST-ALC-07** | Zero Denominator Rejection | $F_A = 0.00, F_B = 0.00$ | Raises `InvalidFareInputError` | Defensive guard |

---

### 2.3 Suite 3: Accuracy Tiers, Recalculation & Provenance Tests
*Target Module:* `backend/app/fares/service.py`

| Test ID | Scenario Description | Pre-Condition | Action / Expectation |
| :--- | :--- | :--- | :--- |
| **TEST-ACC-01** | Conservative Top 1 Aggregation | Initial match search returns Top 1 | `composite_accuracy == "MATRIX_SCREENING"`. `shared_journey_source == "provider_road_network_route"`. `solo_baseline_a_source == "provider_matrix_table"`. |
| **TEST-ACC-02** | Proposal 2..N Matrix Tier | Initial match search returns Proposal 2 | All components are `"provider_matrix_table"`. `composite_accuracy == "MATRIX_SCREENING"`. |
| **TEST-ACC-03** | On-Demand Enrichment Recalculation | User requests detail on Proposal 2 | Enrichment updates shared distance; fare engine re-evaluates; `shared_journey_source` upgrades to `"provider_road_network_route"`. |
| **TEST-ACC-04** | Provider Fallback Tiering | Routing provider raises timeout / 503 | Fallback distance used; fare engine tags `CALIBRATED_FALLBACK`. |

---

### 2.4 Suite 4: Viewer-Centric API Authorization & Privacy Tests
*Target Module:* `backend/app/api/v1/endpoints/matching.py`

| Test ID | Scenario Description | Expected Security & Privacy Behavior |
| :--- | :--- | :--- |
| **TEST-SEC-01** | Passenger A Perspective | Response contains $S_A, F_{\text{solo}, A}, \text{savings}_A, F_{\text{shared}}, S_B$. $F_{\text{solo}, B}$, direct distance B, and savings B are omitted. |
| **TEST-SEC-02** | Passenger B Perspective | Response contains $S_B, F_{\text{solo}, B}, \text{savings}_B, F_{\text{shared}}, S_A$. $F_{\text{solo}, A}$, direct distance A, and savings A are omitted. |
| **TEST-SEC-03** | Unauthorized Caller | JWT caller does not own target request. Returns HTTP 403 / 404. |
| **TEST-SEC-04** | Dual Wire Format Integrity | JSON response contains both float fields and integer `_paise` fields with exact equality. |
| **TEST-SEC-05** | Overlapping Window Range | Departure window crosses midnight. Response returns `surcharge_status = "CONDITIONAL"` and `fare_range`. |

---

### 2.5 Suite 5: Frontend UI & Component Tests
*Target Module:* `frontend/src/features/matching/__tests__/FareBreakdown.test.tsx`

| Test ID | Scenario Description | Expected UI Behavior |
| :--- | :--- | :--- |
| **TEST-UI-01** | Card Share Rendering | Displays "Your Share: ₹127" with green savings badge. |
| **TEST-UI-02** | Negative Savings Warning | Displays "Detour Surcharge: ₹50" in amber when savings are negative. |
| **TEST-UI-03** | Conditional Surcharge Banner | Displays "Estimated fare: ₹219 – ₹274 (crossing night tariff)" when conditional. |
| **TEST-UI-04** | Excluded Charges Disclaimer | Displays disclaimer stating tolls and waiting charges are excluded. |

---

## 3. Regression Confirmation

All existing Phase 1–5A test suites continue passing with zero regressions:
- **Backend pytest:** 140 tests (139 passed, 1 skipped).
- **Frontend vitest:** 30 tests (7 test files passed).
- **Database Schema:** Untouched at migration revision `5b69062ab3ef`.
