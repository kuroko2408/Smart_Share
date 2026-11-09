# Phase 5C Fare Allocation & Passenger Savings — Implementation Report

**Status:** IMPLEMENTED (Local Regression Verified; Hosted Two-User Acceptance Pending)  
**Date:** November 9, 2026  
**Scope:** Solo-fare proportional fare allocation (DEC-008), viewer-scoped privacy protections (DEC-013), deterministic residual paise conservation, and financial eligibility outcomes (POSITIVE/SAVINGS, BREAK_EVEN, NEGATIVE/UNATTRACTIVE, CONDITIONAL).

---

## 1. Executive Summary & Design Decisions Applied

Phase 5C delivers fair cost allocation for black-and-yellow taxi carpooling in Mumbai, consuming Phase 5B pre-trip fare estimates and generating deterministic contributions and savings.

### 1.1 Proportional-to-Solo-Fare Allocation (DEC-008)
- Each passenger's estimated solo baseline fare serves as their allocation weight:
  $$\text{combined\_solo\_fare} = \text{solo\_fare}_A + \text{solo\_fare}_B$$
  $$\text{quota}_A = \text{shared\_fare} \times \frac{\text{solo\_fare}_A}{\text{combined\_solo\_fare}}$$
  $$\text{quota}_B = \text{shared\_fare} \times \frac{\text{solo\_fare}_B}{\text{combined\_solo\_fare}}$$
- Higher solo fare commuters contribute proportionally more, while shorter/lower solo fare commuters contribute less. Arbitrary equal splits are prohibited when solo fares differ.

### 1.2 Exact Sum Conservation & Driver Gross Fare Invariance
- Driver receives 100% of the agreed shared trip fare:
  $$\text{contribution}_A + \text{contribution}_B \equiv \text{shared\_fare}$$
- Driver's agreed gross fare is **never** reduced to manufacture passenger savings.
- Platform-funded discounts and match-score promotional discounts are **not** implemented.
- Deterministic residual rounding (`ROUND_HALF_UP` on Passenger A, exact residual to Passenger B) guarantees sum conservation down to 0 paise without floating-point IEEE 754 drift.

### 1.3 Economic Outcomes & Savings Guarantee
<<<<<<< HEAD
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
=======
- Economic outcomes are classified into strict states:
  1. **POSITIVE / SAVINGS (`shared_fare < combined_solo_fare`):** Both passengers pay less than their own solo fare ($\text{savings}_A > 0$, $\text{savings}_B > 0$, subject to paise rounding). Marked as economically beneficial.
  2. **BREAK_EVEN (`shared_fare == combined_solo_fare` within ±₹0.01 tolerance):** Neither passenger is told they save money ($\text{savings} = 0$).
  3. **NEGATIVE / UNATTRACTIVE (`shared_fare > combined_solo_fare`):** Shared journey is more expensive than riding solo. Negative combined savings are truthfully reported. Proposal compatibility is preserved while clearly flagging economic unattractiveness.
  4. **CONDITIONAL:** When departure time spans the Asia/Kolkata night surcharge boundary (00:00–05:00 IST), day and night tariffs are evaluated as distinct scenarios.

### 1.4 Privacy & DEC-013 Bilateral Consent
- In accordance with DEC-013 (approved 2026-11-08):
  - Passenger B's solo baseline, individual savings, and exact contribution are **never** disclosed to Passenger A without bilateral consent.
  - Direct solo baselines and private savings remain redacted even when bilateral consent is granted (only exact contribution is disclosed upon consent).
  - Unilateral response exposure is strictly viewer-scoped: the authenticated rider sees only their own solo baseline, allocated share, individual savings, and the total shared trip fare.
  - Consent is managed via append-only audit events in `public.match_disclosure_consent_events`.

---

## 2. Fare Discrepancy & Negative Economics Investigation

The user-provided reciprocal proposal screenshots show these exact displayed wire amounts:

| Metric | Passenger A | Passenger B | Combined |
|---|---:|---:|---:|
| Solo baseline estimate | ₹192.96 | ₹83.61 | ₹276.57 |
| Proportional contribution | ₹197.63 | ₹85.64 | ₹283.27 |
| Individual savings | −₹4.67 | −₹2.03 | −₹6.70 |

- **Analysis:** This result is **NEGATIVE** economics ($\text{Shared ₹283.27} > \text{Combined Solo ₹276.57}$). This is not a math defect or allocation error; the pooled road itinerary exceeded the combined separate trips by approximately 0.31 km.
- **Fairness & Truthfulness:** The system truthfully flags this match as "Taking two separate rides is estimated to cost less overall than sharing." The driver's agreed gross fare of ₹283.27 is **not** reduced. Both contributions sum exactly to ₹283.27 ($197.63 + 85.64 = 283.27$).
>>>>>>> 1165930 (Project report)

---

## 3. Architecture & Implementation Modules

### Backend Modules
- [`backend/app/fares/allocation.py`](file:///home/kuroko24/Smart_Share/backend/app/fares/allocation.py): Core allocation engine computing integer-paise proportional shares, residual rounding, and economic assessments.
- [`backend/app/fares/consent.py`](file:///home/kuroko24/Smart_Share/backend/app/fares/consent.py): Append-only DEC-013 consent state management.
- [`backend/app/fares/disclosure.py`](file:///home/kuroko24/Smart_Share/backend/app/fares/disclosure.py): Consent notice text versioning (`DEC-013-2026-11-08-v1`) and SHA-256 fare snapshot fingerprinting.
- [`backend/app/models/match_disclosure_consent.py`](file:///home/kuroko24/Smart_Share/backend/app/models/match_disclosure_consent.py): SQLAlchemy model for `match_disclosure_consent_events`.
- [`backend/app/api/v1/endpoints/matching.py`](file:///home/kuroko24/Smart_Share/backend/app/api/v1/endpoints/matching.py): Matches endpoint integrating consent lookup, viewer privacy scoping, and consent grant/revoke routes (`POST /matches/{id}/disclosure-consent`, `DELETE /matches/{id}/disclosure-consent`).

<<<<<<< HEAD
| Verification Suite | Tool | Scope | Result | Details |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Unit Tests** | `pytest` 9.2.0 | `backend/app/tests/` | **181 passed, 1 skipped** | All tariff, detour, routing, and allocation tests passed |
| **Backend Code Quality** | `ruff check` | `backend/` | **0 errors** | Clean import sorting, no unused variables or style violations |
| **Backend Formatting** | `ruff format --check` | `backend/` | **73 files clean** | Exact PEP 8 / black-compatible formatting |
| **Frontend Tests** | `vitest` 4.1.12 | `frontend/src/` | **32 passed (7 files)** | Smoke, auth, profile, ride requests, matching allocation |
| **Frontend Linter** | `oxlint` | `frontend/src/` | **0 errors, 0 warnings** | Checked with standard rules |
| **Frontend Typecheck** | `tsc --noEmit` | `frontend/` | **0 type errors** | Strict TypeScript compilation clean |
| **Frontend Build** | `vite build` | Production client | **Success** | Production bundle generated |
=======
### Frontend Modules
- [`frontend/src/types/matching.ts`](file:///home/kuroko24/Smart_Share/frontend/src/types/matching.ts): TypeScript interfaces for `MatchFareEstimate`, `FareAllocationDisclosure`, and economic classifications.
- [`frontend/src/features/ride-requests/MatchResults.tsx`](file:///home/kuroko24/Smart_Share/frontend/src/features/ride-requests/MatchResults.tsx): Proposal card distinguishing total shared taxi fare from viewer's solo estimate, rendering economic status, and managing bilateral consent toggle.
- [`frontend/src/services/ride-requests.ts`](file:///home/kuroko24/Smart_Share/frontend/src/services/ride-requests.ts): Client API methods `grantFareDisclosureConsent` and `withdrawFareDisclosureConsent`.

### Database Persistence & Migrations
- **Table:** `public.match_disclosure_consent_events`
- **Migration:** `c5d013c0a501` (`2026_11_08_c5d013c0a501_add_match_disclosure_consent_events.py`)
- **Status:** Verified applied to development database (`ifdmbwjaysspvysoxfpl`). No new migrations are required.
>>>>>>> 1165930 (Project report)

---

## 4. Verification History & Limitations

<<<<<<< HEAD
> [!NOTE]
> **Verification Boundary:**
> - **Local Automated Verification (COMPLETE):** All mathematical allocation algorithms, sum conservation down to 0 paise, residual rounding, break-even/dissavings states, DEC-013 viewer privacy scoping, API schemas, and frontend presentation are fully verified by automated tests.
> - **Hosted Multi-User Acceptance (PENDING):** Live end-to-end verification involving two separate authenticated commuter accounts interacting across the deployed Supabase/Vercel/FastAPI infrastructure to test bilateral consent workflows remains pending live deployment. No database migrations were executed during this phase.
=======
### Historical Local Verification Results (Clean Baseline Commit `536c92a`)
- **Backend Tests:** 175 passed, 1 skipped (hosted PostGIS network sandbox restriction) in 12.70s.
- **Backend Formatting & Linting:** Clean PEP 8 formatting, 0 ruff errors.
- **Frontend Tests:** 32 tests passed across 7 files in 3.48s.
- **Frontend Typecheck & Build:** `tsc --noEmit` clean (0 errors), Vite production bundle built in 0.39s.

### Git Recovery & HEAD Status Notice
- **HEAD Commit:** `eef01c7` (authored by Soham) attempted to merge a parallel revision of Phase 5C (`3dfc1f3`) onto `536c92a`.
- **Blocker:** Merge conflicts were committed unresolved into 13 files in `eef01c7`. Before running local or hosted builds, source code files must be cleanly reconciled.
- **Hosted Two-User Verification Status:** **PENDING**. No live authenticated two-user frontend session has been executed against deployed infrastructure.
>>>>>>> 1165930 (Project report)
