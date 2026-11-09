# Phase 5C Fare Allocation & Passenger Savings — Implementation Report

**Status:** Implemented (Local Verification Complete; Hosted Two-User Acceptance Pending)  
**Date:** November 9, 2026  
**Scope:** Solo-fare proportional fare allocation (DEC-008), viewer-scoped privacy protections (DEC-013), deterministic residual paise conservation, and financial eligibility outcomes (SAVINGS, BREAK_EVEN, UNATTRACTIVE).

---

## 1. Executive Summary & Design Decisions Applied

Phase 5C delivers fair cost allocation for black-and-yellow taxi carpooling in Mumbai, consuming Phase 5B pre-trip fare estimates and generating deterministic contributions and savings.

### 1.1 Proportional-to-Solo-Fare Allocation (DEC-008)
- Each passenger's estimated solo baseline fare serves as their allocation weight:
  $$W_A = \frac{\text{solo\_fare}_A}{\text{combined\_solo\_fare}}, \qquad W_B = \frac{\text{solo\_fare}_B}{\text{combined\_solo\_fare}}$$
  $$\text{combined\_solo\_fare} = \text{solo\_fare}_A + \text{solo\_fare}_B$$
- Higher solo fare commuters contribute proportionally more, while shorter/lower solo fare commuters contribute less. Arbitrary equal splits are prohibited when solo fares differ.

### 1.2 Exact Sum Conservation & Driver Gross Fare Invariance
- Driver receives 100% of the agreed shared trip fare:
  $$\text{contribution}_A + \text{contribution}_B \equiv \text{shared\_fare}$$
- Driver's agreed gross fare is **never** reduced to manufacture passenger savings.
- Platform-funded discounts and match-score promotional discounts are **not** implemented.
- Deterministic residual rounding (`ROUND_HALF_UP` on Passenger A, remainder to Passenger B) guarantees sum conservation down to 0 paise without IEEE 754 drift.

### 1.3 Economic Outcomes & Savings Guarantee
- Economic outcomes are classified into three strict states:
  1. **SAVINGS (`shared_fare < combined_solo_fare`):** Both passengers pay less than their own solo fare ($\text{savings}_A > 0$, $\text{savings}_B > 0$, subject to paise rounding). Marked as economically beneficial.
  2. **BREAK_EVEN (`shared_fare == combined_solo_fare`):** Neither passenger is told they save money ($\text{savings} = 0$, `is_saving = False`).
  3. **UNATTRACTIVE (`shared_fare > combined_solo_fare`):** Sharing costs more than separate solo trips. Neither passenger saves money. Correctly classified as unattractive while preserving routing compatibility.

### 1.4 Privacy & Viewer Scoping (DEC-013)
- Strict viewer-scoped disclosure: Each passenger sees their own solo baseline, allocated contribution, and personal savings.
- Co-passenger solo baseline, allocated contribution, and individual savings are redacted (`None`/hidden) prior to bilateral consent.
- Driver agreed gross fare remains transparently displayed to both commuters.

---

## 2. Modified & Created Artifacts

- [`backend/app/fares/models.py`](file:///home/asta/Projects/Smart_Share/backend/app/fares/models.py): Added `EconomicStatus`, `PassengerAllocation`, `FareAllocationResult`.
- [`backend/app/fares/allocation.py`](file:///home/asta/Projects/Smart_Share/backend/app/fares/allocation.py): Core proportional allocation math, residual rounding, and invariant checks.
- [`backend/app/fares/service.py`](file:///home/asta/Projects/Smart_Share/backend/app/fares/service.py): Integrated Phase 5C allocation service into match lifecycle.
- [`backend/app/api/v1/endpoints/matching.py`](file:///home/asta/Projects/Smart_Share/backend/app/api/v1/endpoints/matching.py): Enforced viewer scoping and privacy redaction on match proposal endpoints.
- [`frontend/src/features/ride-requests/MatchResults.tsx`](file:///home/asta/Projects/Smart_Share/frontend/src/features/ride-requests/MatchResults.tsx): UI cards for fare allocation, economic status badges, and DEC-013 privacy notices.
- [`docs/phase5c-implementation-report.md`](file:///home/asta/Projects/Smart_Share/docs/phase5c-implementation-report.md): This report.
- [`docs/phase5c-testing-report.md`](file:///home/asta/Projects/Smart_Share/docs/phase5c-testing-report.md): Detailed verification test results.
- [`docs/phase5c-integration-report.md`](file:///home/asta/Projects/Smart_Share/docs/phase5c-integration-report.md): Integration and architecture contract report.

---

## 3. Local Verification Results

All local automated tests, linters, type checks, and production builds completed with 100% pass rates:

| Verification Suite | Tool | Scope | Result | Details |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Unit Tests** | `pytest` 9.2.0 | `backend/app/tests/` | **181 passed, 1 skipped** | All tariff, detour, routing, and allocation tests passed |
| **Backend Code Quality** | `ruff check` | `backend/` | **0 errors** | Clean import sorting, no unused variables or style violations |
| **Backend Formatting** | `ruff format --check` | `backend/` | **73 files clean** | Exact PEP 8 / black-compatible formatting |
| **Frontend Tests** | `vitest` 4.1.12 | `frontend/src/` | **32 passed (7 files)** | Smoke, auth, profile, ride requests, matching allocation |
| **Frontend Linter** | `oxlint` | `frontend/src/` | **0 errors, 0 warnings** | Checked with standard rules |
| **Frontend Typecheck** | `tsc --noEmit` | `frontend/` | **0 type errors** | Strict TypeScript compilation clean |
| **Frontend Build** | `vite build` | Production client | **Success** | Production bundle generated |

---

## 4. Distinction Between Local Verification & Hosted Acceptance

> [!NOTE]
> **Verification Boundary:**
> - **Local Automated Verification (COMPLETE):** All mathematical allocation algorithms, sum conservation down to 0 paise, residual rounding, break-even/dissavings states, DEC-013 viewer privacy scoping, API schemas, and frontend presentation are fully verified by automated tests.
> - **Hosted Multi-User Acceptance (PENDING):** Live end-to-end verification involving two separate authenticated commuter accounts interacting across the deployed Supabase/Vercel/FastAPI infrastructure to test bilateral consent workflows remains pending live deployment. No database migrations were executed during this phase.
