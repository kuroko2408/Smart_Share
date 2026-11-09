# Phase 6A Bilateral Consent Workflow — Integration Report

**Status:** Integrated Locally (Hosted Acceptance Pending)  
**Date:** November 9, 2026  

---

## 1. System Integration & Workflow Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor CommuterA as Commuter A
    participant UI as Smart Share Frontend
    participant API as FastAPI Matching Endpoint
    participant ConsentService as Consent & Fares Service
    participant DB as Postgres Audit Log
    actor CommuterB as Commuter B

    Note over CommuterA,CommuterB: Phase 5C Match Discovered (Unconsented)
    CommuterA->>UI: View Match Proposal
    UI->>API: GET /matches/{proposal_id}?request_id={req_a}
    API->>ConsentService: load_proposal_consent_states()
    ConsentService-->>API: { A: False, B: False }
    API-->>UI: Proposal (co_passenger_contribution: null, allocation: null)
    UI-->>CommuterA: Display Solo Baseline, Your Allocation, Consent Notice

    Note over CommuterA: Commuter A Grants Consent
    CommuterA->>UI: Click "I agree to exact disclosure"
    UI->>API: POST /matches/{proposal_id}/disclosure-consent?request_id={req_a}
    API->>ConsentService: record_consent_event(action="GRANTED")
    ConsentService->>DB: INSERT MatchDisclosureConsentEvent (A: GRANTED)
    API-->>UI: exact_disclosure_available: false (A: true, B: false)
    UI-->>CommuterA: "Your consent is recorded. Waiting for other passenger."

    Note over CommuterB: Commuter B Views & Grants Consent
    CommuterB->>UI: View Match Proposal
    UI->>API: GET /matches/{proposal_id}?request_id={req_b}
    API-->>UI: exact_disclosure_available: false (A: true, B: false)
    UI-->>CommuterB: "Other passenger has consented. Your consent required."
    CommuterB->>UI: Click "I agree to exact disclosure"
    UI->>API: POST /matches/{proposal_id}/disclosure-consent?request_id={req_b}
    API->>ConsentService: record_consent_event(action="GRANTED")
    ConsentService->>DB: INSERT MatchDisclosureConsentEvent (B: GRANTED)
    API-->>UI: exact_disclosure_available: true (both consented!)
    UI-->>CommuterB: Display Exact Contributions (co_passenger_contribution revealed)

    Note over CommuterA,CommuterB: Both Commuters Now See Exact Contribution
    CommuterA->>UI: Refresh / View Match Proposal
    UI->>API: GET /matches/{proposal_id}?request_id={req_a}
    API-->>UI: exact_disclosure_available: true
    UI-->>CommuterA: Display Exact Contributions (B's contribution revealed)

    Note over CommuterA: Commuter A Revokes Consent
    CommuterA->>UI: Click "Withdraw my consent"
    UI->>API: DELETE /matches/{proposal_id}/disclosure-consent?request_id={req_a}
    API->>ConsentService: record_consent_event(action="REVOKED")
    ConsentService->>DB: INSERT MatchDisclosureConsentEvent (A: REVOKED)
    API-->>UI: exact_disclosure_available: false
    UI-->>CommuterA: Exact amounts immediately hidden again
```

---

## 2. API Contract Payloads

### 2.1 Unconsented or Unilateral State
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
  },
  "message": "Your exact disclosure consent has been recorded."
}
```

### 2.2 Bilateral Active State
```json
{
  "data": {
    "consent_text_version": "DEC-013-2026-11-08-v1",
    "consent_notice": "If you consent, the other rider will see your exact contribution...",
    "your_consent_active": true,
    "co_passenger_consent_active": true,
    "exact_disclosure_available": true,
    "allocation": {
      "policy": "PROPORTIONAL_TO_SOLO_BASELINE",
      "shared_total": 240.0,
      "shared_total_paise": 24000,
      "your_contribution": 133.33,
      "your_contribution_paise": 13333,
      "co_passenger_contribution": 106.67,
      "co_passenger_contribution_paise": 10667,
      "your_savings": 16.67,
      "your_savings_paise": 1667,
      "your_savings_percent": "11.1100"
    },
    "conditional_scenarios": []
  },
  "message": "Exact disclosure consent status retrieved."
}
```

---

## 3. Hosted Two-User Acceptance Checklist

- [x] Local integration verified (9 backend integration tests passing).
- [x] Local frontend component workflow verified (6 Vitest tests passing).
- [x] DEC-013 privacy gating verified against accidental serialization leaks.
- [x] Sum conservation ($S_A + S_B \equiv F_{\text{shared}}$) preserved in both paise and rupees.
- [x] Driver gross fare remains untouched across all consent transitions.
- [ ] Deploy migration `c5d013c0a501` to hosted Supabase database (after PO approval).
- [ ] Authenticate two live user sessions on hosted environment.
- [ ] Confirm real-time mutual consent toggles co-passenger contribution on both mobile/desktop screens.
