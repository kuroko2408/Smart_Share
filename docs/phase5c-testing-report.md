<<<<<<< HEAD
# Phase 5C Fare Allocation — Testing Report

**Status:** Complete  
=======
# Phase 5C Fare Allocation & Privacy — Testing Report

**Status:** CONDITIONAL PASS (Automated Invariant & Component Tests Pass; Hosted Two-User Acceptance Pending)  
>>>>>>> 1165930 (Project report)
**Date:** November 9, 2026  
**Scope:** Verification of Phase 5C proportional fare allocation (DEC-008), economic assessments, DEC-013 privacy gating, and component UI presentation.

---

## 1. Mathematical and Financial Invariants Verification

The Phase 5C allocation engine enforces 12 core mathematical and financial invariants, verified by automated unit tests:

| Invariant # | Description | Test Function | Test Outcome |
| :--- | :--- | :--- | :--- |
| **INV-1** | Contributions are non-negative ($C_A \ge 0, C_B \ge 0$). | `test_dec008_allocation_conserves_paise_and_screens_the_reported_negative_case` | **PASS (Local)** |
| **INV-2** | Exact sum conservation: $C_A + C_B \equiv F_{\text{shared}}$ in integer paise and Decimal. | `test_dec008_allocation_conserves_paise_and_screens_the_reported_negative_case` | **PASS (Local)** |
| **INV-3** | Proportional weighting: $F_A > F_B \implies C_A > C_B$. | `test_synthetic_detour_fare_allocation_matrix` | **PASS (Local)** |
| **INV-4** | When $F_{\text{shared}} < F_A + F_B$, both passengers save money. | `test_synthetic_detour_fare_allocation_matrix` | **PASS (Local)** |
| **INV-5** | When $F_{\text{shared}} == F_A + F_B$, `BREAK_EVEN` is reported and no savings are claimed. | `test_synthetic_detour_fare_allocation_matrix` | **PASS (Local)** |
| **INV-6** | When $F_{\text{shared}} > F_A + F_B$, `NEGATIVE` is reported with negative savings. | `test_dec008_allocation_conserves_paise_and_screens_the_reported_negative_case` | **PASS (Local)** |
| **INV-7** | No fabricated savings in break-even or dissavings (`is_saving = False`, `savings = 0.00`). | `test_synthetic_detour_fare_allocation_matrix` | **PASS (Local)** |
| **INV-8** | Rounding cannot create false savings claims in micro-fare edge cases. | `test_proportional_allocation_micro_fare_boundary_grid` | **PASS (Local)** |
| **INV-9** | Solo baseline estimates remain unchanged by allocation. | `test_synthetic_detour_fare_allocation_matrix` | **PASS (Local)** |
| **INV-10** | Original shared trip fare remains unchanged by allocation. | `test_dec008_allocation_conserves_paise_and_screens_the_reported_negative_case` | **PASS (Local)** |
| **INV-11** | Driver's agreed gross fare is never reduced or discounted. | `test_dec008_allocation_conserves_paise_and_screens_the_reported_negative_case` | **PASS (Local)** |
| **INV-12** | Boundary grid around minimum fare exhausts all potential sign flip edge cases. | `test_proportional_allocation_micro_fare_boundary_grid` | **PASS (Local)** |

---

## 2. Privacy & DEC-013 Consent Verification

| Test Case | Description | Test Outcome |
| :--- | :--- | :--- |
| **TEST-PRIV-01** | Co-passenger solo baseline and solo distance are completely redacted from proposal JSON. | **PASS (Local)** |
| **TEST-PRIV-02** | Exact allocation object is `None` / omitted prior to bilateral affirmative consent. | **PASS (Local)** |
| **TEST-PRIV-03** | Co-passenger private savings remain redacted even when bilateral consent is granted. | **PASS (Local)** |
| **TEST-PRIV-04** | Bilateral consent reveals `your_contribution` and `co_passenger_contribution` such that $C_A + C_B == F_{\text{shared}}$. | **PASS (Local)** |
| **TEST-PRIV-05** | Unauthorized request ID access attempt fails authorization check (HTTP 403 Forbidden). | **PASS (Local)** |
| **TEST-PRIV-06** | Revocation by either party immediately revokes exact disclosure availability. | **PASS (Local)** |

---

## 3. Frontend Presentation Verification

| Test Case | Component | Verification Goal | Outcome |
| :--- | :--- | :--- | :--- |
| **FE-ALLOC-01** | `MatchResults.tsx` | Clearly distinguishes total shared taxi fare, separate solo estimate, and allocated share. | **PASS (Local)** |
| **FE-ALLOC-02** | `MatchResults.tsx` | Renders economic status warning banner for negative economics (unattractive match). | **PASS (Local)** |
| **FE-ALLOC-03** | `MatchResults.tsx` | Renders DEC-013 privacy notice, consent toggle button, and consented scenario breakdown. | **PASS (Local)** |
| **FE-ALLOC-04** | `MatchResults.tsx` | Renders separate conditional DAY and NIGHT scenario tabs when crossing midnight boundary. | **PASS (Local)** |

---

## 4. Historical Test Execution Summary (Clean Baseline `536c92a`)

```text
Backend Pytest Suite:
- Focused Fare & Matching Tests: 51 passed in 0.66s
- Full Sandboxed Suite: 175 passed, 1 skipped (hosted PostGIS network sandbox restriction) in 12.70s
- Live PostGIS Isolated Run: 1 passed in 0.49s (with transaction rollback)
- Code Quality: ruff check (0 errors), ruff format (clean)

Frontend Vitest Suite:
- 7 test files, 32 passed in 3.48s
- Code Quality: oxlint (0 errors), tsc --noEmit (0 errors)
- Production Build: vite build (Success, 0.39s)
```
<<<<<<< HEAD
backend/app/tests/test_fares.py: 37 passed
backend/app/tests/test_matching_phase5a.py: 24 passed
Full backend suite: 181 passed, 1 skipped
Frontend vitest suite: 32 passed
Total automated tests executed: 213 tests (100% passing)
```
=======

---

## 5. Current Codebase Status & Outstanding Verification

> [!WARNING]
> **Source Tree State Notice:**
> Commit `eef01c7` contained unresolved Git merge conflict markers across 13 source files. The automated test passes recorded above reflect the clean baseline implementation (`536c92a`). The source tree must be reconciled to restore automated test execution.

> [!IMPORTANT]
> **Pending Hosted Acceptance:**
> - Live verification across two distinct authenticated commuter accounts interacting on hosted infrastructure (Render / Vercel / Supabase) has **not yet been executed**.
> - End-to-end evidence collection (live network logs, Supabase database row queries) remains **PENDING**.
>>>>>>> 1165930 (Project report)
