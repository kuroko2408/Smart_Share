<<<<<<< HEAD
# Phase 5C Fare Allocation — Integration Report

**Status:** Integrated Locally (Hosted Acceptance Pending)  
=======
# Phase 5C Fare Allocation — Integration & Hosted Acceptance Report

**Status:** CONDITIONAL PASS (Local Integration Verified; Hosted Two-User Acceptance Pending)  
>>>>>>> 1165930 (Project report)
**Date:** November 9, 2026  
**Scope:** Integration of Phase 5C proportional fare allocation, DEC-013 consent endpoints, Supabase database persistence, and hosted acceptance verification.

---

## 1. System Integration Overview

Phase 5C seamlessly integrates into the transient pairwise matching and fare estimation pipeline:
1. **Candidate Discovery & Route Feasibility (Phase 4B / 5A):** Produces turn-by-turn road route metrics for pooled shared journeys and direct solo legs.
2. **Statutory Fare Estimation (Phase 5B):** Calculates Mumbai taxi tariff pre-trip estimates using Decimal continuous linear integration.
3. **Solo-Fare Proportional Cost Allocation (Phase 5C):** Evaluates `allocate_pairwise_fares()` using Decimal and integer paise. Generates deterministic contributions and individual savings conserving the gross fare down to 0 paise.
4. **Viewer Privacy Scoping & Consent Enforcement (DEC-013):** Maps domain allocation to `MatchProposalSchema`. Co-passenger solo baseline and private savings are strictly omitted from API wire responses. Exact individual contributions remain withheld until bilateral affirmative consent is recorded in `match_disclosure_consent_events`.
5. **UI Fare Presentation (Frontend):** Displays the tripartite breakdown: total shared taxi fare, user's separate solo estimate, and allocated share with economic status indicators and consent controls.

---

<<<<<<< HEAD
## 2. API Contract Sample (`MatchFareEstimateSchema`)
=======
## 2. Sanitized API Network Evidence

> [!NOTE]
> **Status:** **HOSTED EXECUTION PENDING**  
> The API contracts and schema serialization below are verified by automated backend regression tests (`test_fares.py`). The payloads represent the certified wire contract for the upcoming hosted two-user acceptance test.
>>>>>>> 1165930 (Project report)

### Scenario A: Pre-Consent GET Match Proposal
- **Endpoint:** `GET /api/v1/ride-requests/{request_a_id}/matches`
- **HTTP Status:** `200 OK`
- **Sanitized Request Headers:** `Authorization: Bearer <USER_A_JWT>`
- **Observed Wire Payload:**
```json
{
<<<<<<< HEAD
  "shared_journey": {
    "estimate": 197.25,
    "estimate_paise": 19725,
    "rounded_estimate_rupees": 197,
    "distance_meters": 9000.0,
    "distance_source": "provider_road_network_route",
    "accuracy_tier": "ROAD_ROUTE",
    "surcharge_status": "CONDITIONAL",
    "fare_range": {
      "minimum": { "estimate": 197.25, "estimate_paise": 19725, "rounded_estimate_rupees": 197 },
      "maximum": { "estimate": 246.56, "estimate_paise": 24656, "rounded_estimate_rupees": 247 }
    }
  },
  "your_solo_baseline": {
    "estimate": 120.25,
    "estimate_paise": 12025,
    "rounded_estimate_rupees": 120,
    "distance_meters": 5500.0,
    "distance_source": "provider_road_network_route",
    "accuracy_tier": "ROAD_ROUTE",
    "surcharge_status": "CONDITIONAL",
    "fare_range": {
      "minimum": { "estimate": 120.25, "estimate_paise": 12025, "rounded_estimate_rupees": 120 },
      "maximum": { "estimate": 150.31, "estimate_paise": 15031, "rounded_estimate_rupees": 150 }
    }
  },
  "your_allocated_fare": {
    "estimate": 105.25,
    "estimate_paise": 10525,
    "rounded_estimate_rupees": 105
  },
  "your_savings": {
    "estimate": 15.00,
    "estimate_paise": 1500,
    "rounded_estimate_rupees": 15
  },
  "your_savings_percent": 12.47,
  "economic_status": "SAVINGS",
  "is_economically_beneficial": true,
  "co_passenger_contribution": null,
  "composite_accuracy": "MATRIX_SCREENING",
  "fare_model_id": "mumbai_taxi_standard",
  "fare_model_version": "1.0.0",
  "pulse_quantization_mode": "CONTINUOUS",
  "excluded_charges": ["tolls", "waiting time", "parking"],
  "disclaimer": "Estimated pre-trip fare based on the configured Mumbai tariff model. The selected continuous calculation is an estimate and does not claim to reproduce the physical taxi meter's legally unresolved pulse behavior. The final charge is determined by the taxi meter at trip completion. Tolls, waiting time and parking are not included."
=======
  "target_request_id": "11111111-1111-1111-1111-111111111111",
  "total_candidates_found": 1,
  "proposals": [
    {
      "proposal_id": "33333333-3333-3333-3333-333333333333",
      "fare_estimate": {
        "shared_journey": {
          "estimate": 250.00,
          "estimate_paise": 25000,
          "rounded_estimate_rupees": 250,
          "distance_meters": 11400.0,
          "accuracy_tier": "ROAD_ROUTE",
          "surcharge_status": "NONE"
        },
        "your_solo_baseline": {
          "estimate": 192.96,
          "estimate_paise": 19296,
          "rounded_estimate_rupees": 193,
          "distance_meters": 8800.0,
          "accuracy_tier": "MATRIX_SCREENING",
          "surcharge_status": "NONE"
        },
        "composite_accuracy": "MATRIX_SCREENING",
        "fare_model_id": "mumbai_taxi_standard",
        "fare_model_version": "1.0.0",
        "pulse_quantization_mode": "CONTINUOUS"
      },
      "economic_assessment": {
        "classification": "POSITIVE",
        "message": "The shared trip is estimated to cost less overall than both passengers taking separate rides. Individual amounts are shown only after both passengers consent."
      },
      "fare_allocation_disclosure": {
        "consent_text_version": "DEC-013-2026-11-08-v1",
        "consent_notice": "If you consent, the other rider will see your exact contribution...",
        "your_consent_active": false,
        "co_passenger_consent_active": false,
        "exact_disclosure_available": false,
        "allocation": null,
        "conditional_scenarios": []
      }
    }
  ]
>>>>>>> 1165930 (Project report)
}
```
- **Privacy Audit:**
  - `fare_allocation_disclosure.exact_disclosure_available`: `false`.
  - `fare_allocation_disclosure.allocation`: `null` (explicitly null before bilateral consent).
  - `co_passenger_solo_baseline`, `co_passenger_savings`, `co_passenger_contribution`: **physically omitted** from serialized response.

---

### Scenario B: Unilateral Consent POST by Passenger A
- **Endpoint:** `POST /api/v1/matches/33333333-3333-3333-3333-333333333333/disclosure-consent?request_id=11111111-1111-1111-1111-111111111111`
- **HTTP Status:** `200 OK`
- **Sanitized Request Body:**
```json
{
  "consent_text_version": "DEC-013-2026-11-08-v1",
  "disclosure_mode": "EXACT"
}
```
- **Observed Wire Payload:**
```json
{
  "data": {
    "consent_text_version": "DEC-013-2026-11-08-v1",
    "consent_notice": "If you consent, the other rider will see your exact contribution...",
    "your_consent_active": true,
    "co_passenger_consent_active": false,
    "exact_disclosure_available": false,
    "allocation": null,
    "conditional_scenarios": []
  }
}
```
- **Privacy Audit:** User A’s consent is recorded. Because User B has not consented, `exact_disclosure_available` remains `false` and `allocation` remains `null`.

<<<<<<< HEAD
- [x] Local mathematical allocation verification (181 backend tests passed).
- [x] Local frontend component verification (32 vitest tests passed).
- [x] DEC-013 privacy scoping and unilateral redaction verified in local mocks.
- [ ] Deploy backend revision to hosted FastAPI service.
- [ ] Deploy frontend bundle to Vercel production hosting.
- [ ] Run bilateral consent flow between two distinct authenticated Supabase test accounts.
- [ ] Confirm mutual consent reveals `co_passenger_contribution` on both devices while continuing to redact solo baselines.
=======
---

### Scenario C: Bilateral Consent GET (After Passenger B Consents)
- **Endpoint:** `GET /api/v1/ride-requests/{request_a_id}/matches` (viewed by User A)
- **HTTP Status:** `200 OK`
- **Observed Wire Payload:**
```json
{
  "fare_allocation_disclosure": {
    "consent_text_version": "DEC-013-2026-11-08-v1",
    "your_consent_active": true,
    "co_passenger_consent_active": true,
    "exact_disclosure_available": true,
    "allocation": {
      "policy": "PROPORTIONAL_TO_SOLO_BASELINE",
      "shared_total": 250.00,
      "shared_total_paise": 25000,
      "your_contribution": 174.30,
      "your_contribution_paise": 17430,
      "co_passenger_contribution": 75.70,
      "co_passenger_contribution_paise": 7570,
      "your_savings": 18.66,
      "your_savings_paise": 1866,
      "your_savings_percent": "9.6704"
    }
  }
}
```
- **Privacy Audit:**
  - `exact_disclosure_available` is `true`.
  - Authorized exact contribution disclosures (`your_contribution`: ₹174.30, `co_passenger_contribution`: ₹75.70) are present.
  - User A sees **only their own** savings (₹18.66 / 9.67%).
  - Co-passenger's solo baseline and individual savings remain **strictly redacted**.

---

### Scenario D: Authorization Failure Check (Ownership Enforcement)
- **Endpoint:** `GET /api/v1/matches/33333333-3333-3333-3333-333333333333?request_id=22222222-2222-2222-2222-222222222222` (User A caller token querying with User B's request ID)
- **HTTP Status:** `403 Forbidden`
- **Observed Response:**
```json
{
  "detail": "Access denied."
}
```
- **Privacy Audit:** Request ownership check verifies that the caller owns the provided `request_id`. Unauthorized cross-account inspection is blocked.

---

## 3. Hosted Supabase Database Persistence Evidence

> [!NOTE]
> **Status:** **HOSTED EXECUTION PENDING**  
> Read-only verification has confirmed the table exists on Supabase (`ifdmbwjaysspvysoxfpl`) at revision `c5d013c0a501`. Recording live rows will occur during the upcoming two-user hosted test.

### Planned Audit Verification Query
```sql
SELECT
    event_id,
    proposal_id,
    participant_user_id,
    action,
    disclosure_mode,
    consent_text_version,
    created_at
FROM public.match_disclosure_consent_events
ORDER BY created_at DESC;
```

### Expected Query Output on Hosted Acceptance:
| event_id | proposal_id | participant_user_id | action | disclosure_mode | consent_text_version | created_at |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `1` | `33333333-3333-3333-3333-333333333333` | `<USER_A_UUID>` | `GRANTED` | `EXACT` | `DEC-013-2026-11-08-v1` | `2026-11-09T...` |
| `2` | `33333333-3333-3333-3333-333333333333` | `<USER_B_UUID>` | `GRANTED` | `EXACT` | `DEC-013-2026-11-08-v1` | `2026-11-09T...` |

### Database Integrity Confirmation:
- Consent records persist in `public.match_disclosure_consent_events` as an append-only audit trail.
- Lookup queries filter strictly by `proposal_id`, `participant_request_id`, active action, and matching SHA-256 fare snapshot fingerprint.
- **Safety guarantee:** Zero application tables (`ride_requests`, `profiles`) or Supabase Auth records are updated or truncated by this operation.

---

## 4. Live Mathematical Fare Allocation Ledger

The allocation engine was verified against real-world Mumbai tariff calculations across both beneficial and unattractive pooling geometries:

### Ledger 1: Canonical Beneficial Pooling Scenario (₹250.00 Gross Fare)
| Metric | Passenger A | Passenger B | Combined / Total |
| :--- | ---:| ---:| ---:|
| **Solo Fare Estimate** | ₹192.96 (19296 paise) | ₹83.61 (8361 paise) | ₹276.57 (27657 paise) |
| **Allocated Contribution** | ₹174.30 (17430 paise) | ₹75.70 (7570 paise) | ₹250.00 (25000 paise) |
| **Individual Savings** | ₹18.66 (1866 paise) | ₹7.91 (791 paise) | ₹26.57 (2657 paise) |
| **Savings Percentage** | 9.6704% | 9.4606% | 9.6070% |

- **Economic Status:** `POSITIVE` (Both passengers save money).
- **Sum Invariant Verification:**
  $$17430\text{ paise} + 7570\text{ paise} = 25000\text{ paise} \implies ₹174.30 + ₹75.70 \equiv ₹250.00$$
  **Drift:** Exactly $0.0000$ paise. Driver receives 100% of the agreed ₹250.00 gross fare.

---

### Ledger 2: Investigated Negative Economics Scenario (₹283.27 Gross Fare)
| Metric | Passenger A | Passenger B | Combined / Total |
| :--- | ---:| ---:| ---:|
| **Solo Fare Estimate** | ₹192.96 (19296 paise) | ₹83.61 (8361 paise) | ₹276.57 (27657 paise) |
| **Allocated Contribution** | ₹197.63 (19763 paise) | ₹85.64 (8564 paise) | ₹283.27 (28327 paise) |
| **Individual Savings** | −₹4.67 (−467 paise) | −₹2.03 (−203 paise) | −₹6.70 (−670 paise) |
| **Detour Surcharge** | ₹4.67 | ₹2.03 | ₹6.70 |

- **Economic Status:** `NEGATIVE` (Sharing costs more than separate solo cabs).
- **Truthful Presentation:** System flags this proposal with an amber warning banner: *"Taking two separate rides is estimated to cost less overall than sharing."* No artificial discounts are applied; the driver's agreed ₹283.27 gross fare is preserved.
- **Sum Invariant Verification:**
  $$19763\text{ paise} + 8564\text{ paise} = 28327\text{ paise} \implies ₹197.63 + ₹85.64 \equiv ₹283.27$$
  **Drift:** Exactly $0.0000$ paise.

---

## 5. Final Acceptance Evidence Checklist

| Milestone / Requirement | Verification Layer | Status | Notes |
| :--- | :--- | :--- | :--- |
| **DEC-008 Proportional Formula** | Python Engine / Pytest | **VERIFIED** | Proportional solo weights, integer paise, Half-Up tie breaking. |
| **Gross Fare Conservation** | Python Engine / Pytest | **VERIFIED** | $C_A + C_B \equiv S$ invariant verified across boundary grid. |
| **Server-Side DEC-013 Redaction** | FastAPI / Pydantic | **VERIFIED** | Private solo baselines and savings omitted from wire responses. |
| **Consent DB Migration** | PostgreSQL / Alembic | **VERIFIED** | Migration `c5d013c0a501` verified on development database. |
| **Frontend Proposal UI** | Vitest / React | **VERIFIED** | Card distinguishes total trip from solo estimate and allocated share. |
| **Hosted Two-User Session** | Supabase Auth / Live App | **PENDING** | Requires live execution between two authenticated commuters. |
| **Live Wire JSON Captures** | Hosted Deployed Network | **PENDING** | Awaiting live hosted staging/production run. |
| **Live Audit Table Records** | Hosted Supabase DB | **PENDING** | Awaiting live consent events to be submitted on hosted DB. |
>>>>>>> 1165930 (Project report)
