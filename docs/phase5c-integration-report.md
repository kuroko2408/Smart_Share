<<<<<<< Updated upstream
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
# Phase 5C Integration Report

**Date:** 2026-11-08  
**Result:** CONDITIONAL PASS — migration and hosted PostGIS discovery are verified; authenticated two-user frontend disclosure remains unverified.

## Workflow exercised

1. Reused the existing Phase 5B `estimate_match_fare` output; no tariff values or calculation behavior were changed.
2. Ran proposals through the matching API response serializer in backend tests and verified viewer-scoped fare estimates, economic assessment, notice, and allocation serialization.
3. Verified no allocation appears with neither participant consented, and exact allocation appears only in the serializer when both participant request IDs have current consent for the same fare fingerprint.
4. Tested consent state loading against current/stale snapshots and append-only grant/revoke event construction.
5. Rendered the frontend match results against controlled API response fixtures; verified the notice and no-consent state, then consent action followed by detail refresh to a both-consented response, at which point exact contributions and the current rider's savings render.
6. Applied the existing additive Alembic migration to the confirmed development project. Verified the table's nine columns, two check constraints, two application foreign keys, primary key, composite index, revision `c5d013c0a501`, and zero initial consent events.
7. Ran the repository's live PostGIS integration test with approved development-database connectivity. It passed and rolled back all synthetic test requests.
8. Restarted FastAPI after migration; application startup completed. The sandbox did not permit a separate exec process to connect to the server's localhost listener, so no live HTTP call was made to that restarted process. The frontend was not started for a real-user flow because no authorized login session was available.

## Acceptance checklist

| Area | Result | Evidence / limitation |
|---|---|---|
| FastAPI restart | PASS | Uvicorn startup completed after migration; separate-process HTTP smoke was blocked by sandbox localhost isolation. |
| Allocation integration | PASS in automated tests | Phase 5B estimate inputs feed Decimal/integer-paise allocation; exact conservation checked. |
| Economic warning | PASS in automated tests | ₹283.27 versus ₹276.57 is classified negative; no positive savings claim is produced. |
| API privacy | PASS in local serialization tests | No co-passenger solo baseline or savings fields; allocation is `null` before bilateral consent. |
| Bilateral consent logic | PASS in service/schema tests | Both participant request IDs and current fare snapshot/version are required; revocation event invalidates active consent. |
| Frontend consent flow | PASS in component tests | Notice, affirmative choice, no-thanks behavior, withdrawal control, and consented render path covered. |
| Hosted Supabase authentication | NOT VERIFIED | No real user session or JWT was used for this Phase 5C run. |
| Hosted consent persistence | PARTIAL | The table is present and empty; no real consent grant/revoke was recorded. |
| Two-user exact disclosure | NOT VERIFIED | No authorized test accounts/session were provided. Aggregate data shows one eligible pair, but those owners are not confirmed test accounts. |
| Hosted PostGIS | PASS | Live `test_matching_postgis.py` passed against the development database; its temporary rows were rolled back. |

## Sanitized fare evidence

The supplied proposal screenshots show shared fare estimate **₹283.27** and individual own-solo estimates **₹192.96** and **₹83.61** in reciprocal rider views. Combined solo estimates are **₹276.57**, so the shared estimate is **₹6.70 higher**. No names, request IDs, tokens, credentials, or private location labels are included here. See the implementation report for what can and cannot be inferred about route distance.

## Database safety

The consent migration created only the new audit table and index; it did not alter or delete application records. The isolated PostGIS integration test's synthetic requests were rolled back. No reset, truncation, user/profile deletion, or Supabase Auth modification occurred. No consent rows were created. No Phase 5A/5B schema or fare data changed.

## Outstanding requirements for full PASS

1. Use two authorized development accounts and current active requests to verify each owner can consent only for their request, unilateral consent never returns amounts, bilateral consent returns only the authorized fields, and either revocation suppresses exact amounts.
2. Verify the real authenticated frontend → backend → hosted PostGIS/database workflow and capture sanitized evidence.
3. Re-run backend/frontend regressions after any application deployment and record the deployed revision.

No Phase 6A implementation, group formation, ride acceptance, or payment functionality was started.
<<<<<<< Updated upstream
=======
=======
# Phase 5C Fare Allocation — Integration Report

**Status:** Integrated Locally (Hosted Acceptance Pending)  
**Date:** November 9, 2026  

---

## 1. System Integration Overview

Phase 5C seamlessly integrates into the transient pairwise matching and fare estimation pipeline:
1. **Candidate Discovery & Routing Normalization (Phase 4B / 5A):** Produces turn-by-turn road route metrics for shared pooled journey and direct solo legs.
2. **Statutory Fare Estimation (Phase 5B):** Calculates Mumbai taxi tariff pre-trip estimates for $P_1 \to D_2$ (`shared_journey`), $P_A \to D_A$ (`your_solo_baseline`), and $P_B \to D_B$ (`candidate_solo_baseline`).
3. **Solo-Fare Proportional Cost Allocation (Phase 5C):** Evaluates `calculate_fare_allocation()` using Decimal and integer paise. Generates deterministic contributions and individual savings.
4. **Viewer Privacy Scoping (DEC-013):** Maps domain allocation to `MatchFareEstimateSchema`. Redacts co-passenger solo baselines and contributions unless affirmative bilateral consent is recorded.
5. **UI Fare Presentation (Frontend):** Displays the tripartite breakdown: Original shared trip fare, Solo baseline estimate, and Allocated share with savings or attractiveness indicators.

---

## 2. API Contract Specification (Phase 5C)

### Serialized Proposal `fare_estimate` Object

```json
{
  "shared_journey": {
    "estimate": 197.25,
    "estimate_paise": 19725,
    "rounded_estimate_rupees": 197,
    "distance_meters": 9000.0,
    "distance_source": "provider_road_network_route",
    "accuracy_tier": "ROAD_ROUTE",
    "surcharge_status": "NONE",
    "fare_range": null
  },
  "your_solo_baseline": {
    "estimate": 87.75,
    "estimate_paise": 8775,
    "rounded_estimate_rupees": 88,
    "distance_meters": 4000.0,
    "distance_source": "provider_matrix_table",
    "accuracy_tier": "MATRIX_SCREENING",
    "surcharge_status": "NONE",
    "fare_range": null
  },
  "your_allocation": {
    "allocated_fare": {
      "estimate": 105.20,
      "estimate_paise": 10520,
      "rounded_estimate_rupees": 105
    },
    "savings": {
      "estimate": 15.00,
      "estimate_paise": 1500,
      "rounded_estimate_rupees": 15
    },
    "savings_percent": 12.47,
    "is_saving": true,
    "economic_status": "SAVINGS",
    "is_economically_beneficial": true
  },
  "your_allocated_fare": {
    "estimate": 105.20,
    "estimate_paise": 10520,
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
}
```

---

## 3. Hosted Two-User Acceptance Checklist (Pending Live Gate)

- [x] Local mathematical allocation verification (160 backend tests passed).
- [x] Local frontend component verification (30 vitest tests passed).
- [x] DEC-013 privacy scoping and unilateral redaction verified in local mocks.
- [ ] Deploy backend revision to hosted FastAPI service.
- [ ] Deploy frontend bundle to Vercel production hosting.
- [ ] Run bilateral consent flow between two distinct authenticated Supabase test accounts.
- [ ] Confirm mutual consent reveals `co_passenger_contribution` on both devices while continuing to redact solo baselines.
>>>>>>> 3dfc1f3 (5C)
>>>>>>> Stashed changes
