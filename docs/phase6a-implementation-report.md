# Phase 6A Bilateral Consent Workflow — Implementation Report

**Status:** Implemented (Local Verification Complete; Hosted Two-User Acceptance Pending)  
**Date:** November 9, 2026  
**Scope:** Complete authenticated bilateral consent workflow under DEC-013, persistent audit logging via `match_disclosure_consent_events`, viewer-scoped redaction, consent withdrawal/revocation, and interactive frontend presentation.

---

## 1. Executive Summary & Design Decisions Applied

Phase 6A completes the privacy and consent lifecycle for shared-cost carpooling proposals. Under DEC-013, exact proportional cost allocations can carry an algebraic inference risk ($F_B \approx F_A \times S_B / S_A$). Therefore, co-passenger financial amounts are strictly withheld until **both** participants affirmatively grant informed consent to the identical fare snapshot.

### 1.1 Core Workflow & DEC-013 Policy Enforcement
- **Voluntary & Informed:** Participants review a plain-language explanation of what is shared (exact contribution only), why it is private (inference risk for solo baseline), and that consenting does not accept the ride.
- **Strict Bilateral Disclosure Rule:**
  $$\text{Disclosure Authorized} \iff \text{Consent}(P_A) = \text{GRANTED} \land \text{Consent}(P_B) = \text{GRANTED}$$
  If either commuter has not consented or withdraws consent, co-passenger contribution is strictly suppressed (`None` / hidden).
- **Redaction Invariant:**
  - Co-passenger solo baseline ($F_B$) and co-passenger personal savings are **permanently redacted** (`None`) from all serialized API responses and frontend views, before and after consent.
  - Viewer sees only their own solo baseline, their own allocated contribution, and their own savings.
- **Driver Gross Fare Invariance:**
  - Driver receives 100% of the agreed shared trip fare ($S_A + S_B \equiv F_{\text{shared}}$). No platform discounts or fare cuts are applied.

---

## 2. API Endpoints Implemented

All endpoints enforce JWT Bearer authentication, request ownership verification, and active proposal membership:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/matches/{proposal_id}/disclosure-consent?request_id={owned_request_id}` | Retrieve current DEC-013 consent status (`your_consent_active`, `co_passenger_consent_active`, `exact_disclosure_available`, and allocation if bilateral). |
| `POST` | `/api/v1/matches/{proposal_id}/disclosure-consent?request_id={owned_request_id}` | Submit consent decision (`action: "GRANTED"` or `"REVOKED"`). Requires active notice version `DEC-013-2026-11-08-v1` and `disclosure_mode: "EXACT"`. |
| `DELETE` | `/api/v1/matches/{proposal_id}/disclosure-consent?request_id={owned_request_id}` | Withdraw/revoke current user's consent immediately. Reverts proposal state to hidden exact amounts. |

---

## 3. Persistent Event Audit Logging

Consent decisions are recorded in `public.match_disclosure_consent_events` (migration `c5d013c0a501`):
- Columns: `event_id`, `proposal_id`, `participant_request_id`, `participant_user_id`, `action IN ('GRANTED', 'REVOKED')`, `disclosure_mode = 'EXACT'`, `consent_text_version`, `subject_fingerprint`, `occurred_at`.
- **Idempotency & Duplicate Prevention:** Submitting duplicate grants or redundant revocations is safely detected via `record_consent_event()`, returning existing status without inserting redundant rows.
- **Fare Snapshot Fingerprinting:** Consents are cryptographically bound via SHA-256 fingerprinting of the canonical fare estimate. Any underlying route or tariff change automatically invalidates prior grants.

---

## 4. Frontend Experience & Presentation

Implemented in [`frontend/src/features/ride-requests/MatchResults.tsx`](file:///home/asta/Projects/Smart_Share/frontend/src/features/ride-requests/MatchResults.tsx):
- **Pending State:** Shows privacy disclosure notice, indicators that other passenger is pending/consented without leaking numbers, and actions: "I agree to exact disclosure" or "No thanks".
- **Declined State:** "You chose not to consent in this view. Exact contribution amounts remain hidden." with "Review consent notice" option.
- **Consented (Unilateral):** Displays "Your consent is recorded. The other passenger must also consent before exact amounts are shown." with "Withdraw my consent" button.
- **Consented (Bilateral):** Displays full tripartite breakdown (Shared total, Your share, Other passenger's share, Your savings) with explicit notice that co-passenger solo baselines remain confidential.
- **Error Handling & Mobile Responsiveness:** Fully accessible (`aria-label="Fare contribution disclosure"`), responsive multi-column layout, loading spinners, and mutation error alerts.

---

## 5. Artifacts Modified or Added

- [`backend/app/schemas/matching.py`](file:///home/asta/Projects/Smart_Share/backend/app/schemas/matching.py): Added `action` to `MatchDisclosureConsentRequest`.
- [`backend/app/api/v1/endpoints/matching.py`](file:///home/asta/Projects/Smart_Share/backend/app/api/v1/endpoints/matching.py): Implemented `GET /{proposal_id}/disclosure-consent`, bilateral toggling on proposals, and unified `action` support.
- [`backend/app/tests/conftest.py`](file:///home/asta/Projects/Smart_Share/backend/app/tests/conftest.py): SQLite compiler directives for PostGIS Geography and CheckConstraints.
- [`backend/app/tests/test_bilateral_consent.py`](file:///home/asta/Projects/Smart_Share/backend/app/tests/test_bilateral_consent.py): 9 comprehensive integration tests covering all lifecycle scenarios.
- [`frontend/src/services/ride-requests.ts`](file:///home/asta/Projects/Smart_Share/frontend/src/services/ride-requests.ts): Added `fetchFareDisclosureConsent`.
- [`frontend/src/features/ride-requests/MatchResults.tsx`](file:///home/asta/Projects/Smart_Share/frontend/src/features/ride-requests/MatchResults.tsx): Interactive consent workflow, decline, review, and withdrawal controls.
- [`frontend/src/features/ride-requests/__tests__/BilateralConsent.test.tsx`](file:///home/asta/Projects/Smart_Share/frontend/src/features/ride-requests/__tests__/BilateralConsent.test.tsx): 6 Vitest component tests verifying all UI states.

---

## 6. Verification Boundary

> [!NOTE]
> - **Local Verification (COMPLETE):** All 9 backend test scenarios, 6 frontend test scenarios, linting, formatting, and production builds pass with 100% success.
> - **Hosted Multi-User Acceptance (PENDING):** Live end-to-end testing between two separate physical commuters across deployed Supabase/Vercel/FastAPI infrastructure remains pending hosted environment deployment.
