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
