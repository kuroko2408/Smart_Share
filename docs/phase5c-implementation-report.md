# Phase 5C Implementation Report

**Status:** CONDITIONAL PASS — allocation and consent-gated API/UI behavior are implemented and automated regressions pass. Hosted database migration and two-user authenticated verification remain outstanding.
**Date:** 2026-11-08

## Scope and decisions

Phase 5C consumes the existing Phase 5B `MatchFareEstimate`; it does not change tariff calculations. The Phase 5A routing architecture establishes allocation as Phase 5C scope; its explicit mathematics and visibility rules are defined by DEC-008 and Sections 9–12 of the Phase 5B design, rather than a standalone Phase 5A allocation specification. DEC-008 is implemented for pairwise matches only. DEC-013 was explicitly approved by the Product Owner on 2026-11-08: exact contribution disclosure is permitted only after both participants separately consent to the current inference-risk notice. Consent does not accept a ride. The candidate's solo baseline, solo-route information, and savings are never returned.

No Phase 6A or group/acceptance/payment work was started. The frontend changes here are the minimum result-view consent controls required to avoid exposing exact allocation without bilateral consent.

## Fare discrepancy investigation

The user-provided reciprocal proposal screenshots show these exact displayed wire amounts:

| Value | Amount |
|---|---:|
| Shared journey estimate | ₹283.27 |
| Passenger A's own solo estimate | ₹192.96 |
| Passenger B's own solo estimate | ₹83.61 |
| Combined solo estimates | ₹276.57 |
| Shared fare above combined solo estimates | ₹6.70 |

The estimate therefore classifies as **NEGATIVE**. This does not establish that pooling saves money, and the fare is not adjusted to force savings. The screenshot shows a shared road-network route and individual solo baselines screened from the routing matrix. The inputs are compared as fare estimates from the same Phase 5B tariff model, but their route-source accuracies differ; this adds uncertainty to the comparison. The departure displayed was about 22:01 IST, outside the `[00:00, 05:00)` night window, so a night surcharge does not explain this difference. Whole-rupee display rounding also does not explain it because the exact paise values are available.

The screenshots do not retain unrounded route metres or pre-paise fare values. As an inference only, under the continuous day tariff (`₹33 + ₹21.90/km` after the first 1.5 km), the fare difference is consistent with the pooled route covering roughly 0.31 km more than the two solo baselines combined, with small differences from displayed precision. It cannot be attributed more precisely to route distance versus the shared-vs-matrix routing source without the original proposal route metrics. Phase 5B fare logic was not changed.

## Allocation and economics

For canonical Passenger A and B, allocation is:

`share_A = ROUND_HALF_UP(shared_paise × solo_A_paise / (solo_A_paise + solo_B_paise))`; `share_B = shared_paise − share_A`.

All calculation inputs are validated and processed with `Decimal` and integer paise. Passenger B deterministically receives the residual paise. Contributions must be nonnegative and sum exactly to the shared estimate. Canonical A is selected by stable request UUID ordering, so viewing the same pair from the other rider's request does not change the allocation. Savings are each solo baseline minus that passenger's share; combined savings are the sum of both solo baselines minus the shared total. Percentages are rounded to four decimal places using half-up rounding.

The ₹283.27 example allocates **₹197.63 / ₹85.64** under the approved formula. The corresponding savings are **−₹4.67 / −₹2.03**; both amounts exceed their solo baselines in this negative case. The API exposes the viewer's own share and savings and the co-passenger contribution only after bilateral consent; it does not return the co-passenger baseline or savings. Under DEC-008 proportional allocation, passenger contributions track their solo baselines proportionally: exhaustive boundary checks found no opposite-sign individual savings, although paise rounding can leave one passenger at break-even. The UI avoids a per-person guarantee.

Economic classification is a separate hard comparison of estimated shared cost with combined solo baselines. Negative comparisons display a clear “not a money-saving option” warning; they remain proposals rather than being silently rejected or repriced. Day/night fare ranges are compared as conditional where tariff classification differs.

## DEC-013 consent and privacy

The UI presents the inference notice before affirmative action and provides “No thanks” and withdrawal controls. The API requires the caller to own an active participating request and revalidates that the proposal is current. Exact values are serialized only when each participant request has a current affirmative event for the same proposal, notice version, disclosure mode, and fare snapshot. Either participant can revoke; revocation suppresses exact values. Grants/revocations are append-only audit records. The notice states that a rider may infer another rider's solo baseline from exact contribution information and that consent does not remove this residual risk.

The co-passenger solo baseline, co-passenger savings, and solo-route metrics are not in the allocation schema. Existing shared itinerary and candidate information remains limited to evaluating a proposed shared trip. No general terms or silence are treated as consent.

## API and frontend changes

- Existing match initiation/list/detail responses now include a privacy-safe economic assessment and consent state/notice.
- `POST /api/v1/matches/{proposal_id}/disclosure-consent?request_id=...` records explicit exact-disclosure consent with the required current notice version.
- `DELETE /api/v1/matches/{proposal_id}/disclosure-consent?request_id=...` revokes the participant's consent.
- The allocation object includes shared estimate, both exact contributions, and only the viewer's own savings and percentage. Integer paise fields are authoritative for reconciliation.
- Match results display the economic warning, inference notice, opt-in/decline/withdrawal controls, and consented amounts. No candidate solo fare or savings is displayed.
- API contract details are updated in `docs/04-database-api-contracts.md`.

## Database and migration

One additive migration creates `match_disclosure_consent_events`, including foreign keys to application ride requests and profiles, action/mode constraints, and a proposal/participant/event index. It stores audit metadata and a fare-snapshot fingerprint, not fare amounts. It does not change existing tables, Supabase Auth tables, ride-request state, or Phase 5B tariff data. The generated PostgreSQL SQL was inspected in offline mode. In the follow-up migration fix, the existing migration was applied to the verified development project at `c5d013c0a501`; the table and expected columns were confirmed and its initial event count was zero. No reset, deletion, or truncation occurred.

## Files changed

- Backend allocation, consent, disclosure, response schemas, matching endpoint integration, consent event model, migration, and tests.
- Frontend matching types, API service methods, match results consent UI, and UI tests.
- Decision register, Product Owner decision sheet, fare design/risk/test documents, roadmap, API contract, and Phase 5C reports.

## Limitations and risks

- Hosted authenticated two-user integration was not performed. The development database has two eligible active requests across two owners, but they are not confirmed as authorized test accounts and no login credentials/session are available.
- The consent migration is applied to the verified development database. No consent event was recorded during verification.
- The fare comparison inherits the Phase 5B route accuracy tiers; matrix-screened solo baselines can make economic status uncertain relative to actual road routes.
- Exact contribution disclosure intentionally retains the approved algebraic inference risk.
- The ₹283.27/₹276.57 screenshot inputs are known, but original unrounded route distances are unavailable.
- One existing PostGIS test is skipped because hosted PostGIS is unreachable or network-restricted in the sandbox.

See [testing report](phase5c-testing-report.md) and [integration report](phase5c-integration-report.md) for command-level evidence and final acceptance limits.
