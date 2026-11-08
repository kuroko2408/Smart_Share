# Phase 5B Fare Estimation — Implementation Report

**Status:** Implemented; conditional acceptance pending hosted verification.  
**Scope:** Tariff-based pre-trip fare estimates integrated into existing pairwise matching proposals. No Phase 5C allocation behavior was implemented.

## Design decisions applied

- Continuous linear distance integration is the default pre-trip estimate strategy. `CEILING` and `FLOOR` remain configurable comparison strategies. The setting is `FARE_PULSE_QUANTIZATION_MODE`; set it in the runtime/deployment environment to `CONTINUOUS`, `CEILING`, or `FLOOR`. It defaults to `CONTINUOUS` when unset. Existing `.env` files were not modified.
- The physical meter's pulse behavior remains legally unresolved. Every estimate says it does not claim to reproduce that behavior and distinguishes the estimate from the final taxi-meter charge.
- Monetary tariff calculations use `Decimal`. The configured Mumbai model includes ₹33.00 for the initial 1,500 metres, ₹21.90/km thereafter, 100-metre pulse comparisons, and a 25% night multiplier. Rupee estimates, integer paise, and whole-rupee `ROUND_HALF_UP` outputs are serialized.
- Night time is `[00:00, 05:00)` in `Asia/Kolkata`. Estimates use the shared departure-window midpoint; windows spanning day and night return a conditional day/night fare range.
- Shared route and direct solo route sources are preserved separately. `ROAD_ROUTE`, `MATRIX_SCREENING`, `CALIBRATED_FALLBACK`, and `GEODESIC_ONLY` are the only exposed tiers. Composite accuracy is the weakest material input.
- The matching API exposes the shared journey estimate and only the authenticated request owner's solo baseline. Candidate solo fare is not serialized. Existing passenger metrics are viewer-scoped to avoid exposing another passenger's solo direct distance.
- Fare estimation is informative. An invalid or unsupported fare input yields a null `fare_estimate` and does not discard a feasible match proposal.
- DEC-013 and Phase 5C do not block this isolated work. No allocation, contribution, savings, consent, or split-display fields or calculations were added.

## Implementation overview

The `app.fares` package provides the immutable fare model configuration, in-memory registry, tariff calculation, accuracy mapping, surcharge-window handling, and match-proposal estimator. Existing matching discovery and proposal-detail endpoints call the estimator during proposal serialization, so enriched routes are priced from their current shared-distance value. The existing API response envelope and authentication/ownership checks remain in use.

Frontend match cards show the shared estimate, the viewer's own solo baseline, accuracy, conditional fare range, and disclaimer. Route-distance labels distinguish road routes from matrix and geographic approximations. No result is presented as an accepted group or final charge.

## Changed files

- Backend: `backend/app/fares/{models,registry,service,tariff}.py`, `backend/app/api/v1/endpoints/matching.py`, `backend/app/core/config.py`, `backend/app/schemas/matching.py`.
- Tests: `backend/app/tests/test_fares.py`, `backend/app/tests/test_matching_phase5a.py`.
- Frontend: `frontend/src/types/matching.ts`, `frontend/src/features/ride-requests/MatchResults.tsx`, `frontend/src/features/ride-requests/__tests__/RideRequests.test.tsx`.
- Documentation: `docs/04-database-api-contracts.md`, this report, `docs/phase5b-testing-report.md`, and `docs/phase5b-integration-report.md`. The revised Phase 5B design, model decisions, test strategy, risk analysis, audit, roadmap, and Product Owner decision sheet were already present as working-tree documentation revisions when implementation began.

## API response contract

Every normal proposal response now contains:

```json
{
  "fare_estimate": {
    "shared_journey": {
      "estimate": 164.4,
      "estimate_paise": 16440,
      "rounded_estimate_rupees": 164,
      "distance_meters": 7500,
      "distance_source": "provider_road_network_route",
      "accuracy_tier": "ROAD_ROUTE",
      "surcharge_status": "NONE",
      "fare_range": null
    },
    "your_solo_baseline": { "estimate": 120.6, "estimate_paise": 12060, "rounded_estimate_rupees": 121 },
    "composite_accuracy": "MATRIX_SCREENING",
    "fare_model_id": "mumbai_taxi_standard",
    "fare_model_version": "1.0.0",
    "pulse_quantization_mode": "CONTINUOUS",
    "excluded_charges": ["tolls", "waiting time", "parking"],
    "disclaimer": "Estimated pre-trip fare ..."
  }
}
```

The abbreviated solo object above is illustrative; actual responses include the same amount, provenance, accuracy, and surcharge fields as the shared component. The candidate's solo fare is absent. Fare calculation failures return `fare_estimate: null` while preserving the match result.

## Database and security

No migration, table, persistence layer, or database mutation was added. The source Alembic revision remains `5b69062ab3ef`; hosted revision was not queried during this implementation. The matching endpoint continues to derive identity from the existing verified-auth dependency and checks request ownership before discovery. The added API test uses that endpoint with an injected test principal; it does not claim a real Supabase JWT verification run.

## Limitations and remaining risks

- The hosted frontend-to-Supabase-to-FastAPI-to-PostGIS workflow was not exercised with development accounts. See the integration report.
- Route and fare accuracy cannot exceed the source routing data. `ROAD_ROUTE` is road-network routing, but does not imply live traffic or guarantee the physical route/charge.
- The whole-rupee rounding policy follows the approved design; physical meter pulse behavior is unresolved and not asserted.
- Node/npm emitted a compatibility warning: installed npm 12.2.2 does not list installed Node 20.20.2 as supported. Tests and build nevertheless completed successfully.

## Verdict

**CONDITIONAL PASS** — Phase 5B is implemented and the matching-to-fare API path is covered by an ASGI integration test, with backend/frontend regression checks passing. Hosted authenticated end-to-end verification remains outstanding, so this is not a final hosted acceptance PASS.
