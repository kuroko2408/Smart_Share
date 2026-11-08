# Phase 5C — Fare Behaviour Investigation

**Date:** 2026-11-09  
**Verdict:** CONDITIONAL PASS — deterministic calculation, privacy, UI, and regression checks pass; an authorized hosted two-user frontend session was not available for this investigation.

## Findings

The observed ₹283.27 shared estimate versus ₹192.96 and ₹83.61 solo estimates is a real negative-economic result, not a fare allocation defect. The solo estimates total ₹276.57, so sharing is estimated to cost ₹6.70 more overall. At the observed departure time (about 22:01 IST), the night surcharge does not apply. The shared route estimate came from a road-network route while both direct solo estimates came from matrix screening. All three used the same Phase 5B tariff model, but the route-source accuracy is not identical.

The screenshots contain fare amounts but not route metres or pre-paise tariff values. Therefore the precise distance contribution cannot be recovered from the artifact. As an inference only, the day tariff is consistent with the shared route being roughly 0.31 km longer than the two solo routes combined; the mixed road/matrix provenance also contributes uncertainty. No tariff, route distance, allocation, or savings value was changed to make the outcome look better.

The supplied screenshots do show one equal fare: a shared estimate of ₹192.96 and the viewer's own solo estimate of ₹192.96. That proposal shows 0 m pickup separation, 0 m destination separation, and an 8.8 km shared road route; the direct fare is labelled matrix-screening accuracy. This is consistent with two riders travelling the same corridor and both estimates rounding to the same tariff amount. The screenshot does not expose exact coordinates or raw solo route metres, so equality of the underlying distances cannot be proven. For reference, inverting the day tariff gives approximately 8.804 km for a continuous ₹192.96 estimate; this is an inference, not an observed route distance. The fare equality is legitimate and does not establish a defect. Critically, the shared ₹192.96 must be compared with the sum of two solo rides, not with either individual solo fare: if both solo fares are ₹192.96, the separate total is ₹385.92 and the estimated combined saving is ₹192.96.

Another supplied pair of reciprocal views shows shared ₹283.27 against solo baselines ₹192.96 and ₹83.61, producing the negative ₹6.70 result described above. The two screenshot cases are different match proposals/outcomes and should not be combined into one route calculation.

## Calculation path traced

1. `backend/app/matching/service.py` supplies the target and candidate pickup/destination coordinates and the route result to a `MatchProposal`.
2. `backend/app/matching/detour.py:evaluate_pairwise_detour` builds a matrix in `[pickup A, pickup B, destination A, destination B]` order. It reads A direct distance from `[0][2]` and B direct distance from `[1][3]`.
3. `valid_pairwise_stop_orders()` returns all six topological permutations in which each pickup precedes its own dropoff. The evaluator requires both passengers to be onboard for at least one leg, leaving the four genuinely shared sequences. It computes both passenger journey segments from that passenger's pickup through their own dropoff, evaluates each passenger's own detour tolerance, and picks the lowest total feasible detour.
4. The shared estimate consumes the selected pooled route distance. Each solo baseline consumes that passenger's own direct matrix distance. `estimate_match_fare()` preserves each distance source and accuracy tier, and composite accuracy is the weakest of shared, A solo, and B solo provenance.
5. Phase 5B applies the approved Mumbai tariff separately to each distance, using `Decimal`, configured pulse mode, and the Asia/Kolkata departure window. A window crossing 00:00/05:00 yields day/night ranges rather than an unqualified surcharge assertion.
6. Phase 5C allocates integer paise proportionally to solo baselines. Canonical A receives `ROUND_HALF_UP(shared_paise × solo_A_paise / combined_solo_paise)` and B receives the exact residual. Combined savings are `solo_A + solo_B − shared`; each passenger's savings are their own solo baseline less their own contribution.
7. The API derives a privacy-safe economic classification from the authoritative backend assessment. The frontend presents total shared trip fare, the viewer's own solo estimate, and the aggregate outcome message separately. It does not derive a separate business classification.

## Economic outcomes

The approved one-paise classification tolerance is applied to the integer-paise aggregate comparison: savings over ₹0.01 are `POSITIVE`; costs over ₹0.01 are `NEGATIVE`; a difference from −₹0.01 through +₹0.01 is `BREAK_EVEN`. Each of the two solo fares and the shared fare may shift by up to half a paise, for at most 1.5 paise aggregate rounding uncertainty. With integer-paise values, a directional classification therefore requires at least a two-paise difference. If day and night scenarios yield different classes, the API returns `CONDITIONAL`. This tolerance is a rounding-neutrality rule, not a percentage threshold or a discount.

Economic attractiveness does not determine match compatibility. A valid match remains visible when it is break-even or costs more. Negative outcomes explicitly say that two separate rides are estimated to cost less; no positive saving is displayed. The shared fare is never modified.

The ₹283.27 example allocation is:

| Metric | Passenger A | Passenger B | Combined |
|---|---:|---:|---:|
| Solo baseline | ₹192.96 | ₹83.61 | ₹276.57 |
| Proportional contribution | ₹197.63 | ₹85.64 | ₹283.27 |
| Individual savings | −₹4.67 | −₹2.03 | −₹6.70 |

The contribution sum exactly conserves the shared fare. This confirms both riders pay more than their solo baseline in this example.

Under proportional allocation, one passenger cannot have positive savings while the other has negative savings: before rounding both proportional shares have the same sign relative to their solo baselines, and the deterministic paise residual cannot cross a whole-paise baseline. Paise rounding can make one passenger's savings zero. Regression tests exhaust a boundary grid around the minimum fare to check this invariant. This is a property of the approved allocation policy, not an assumption about all possible allocation policies.

## Controlled route-to-fare matrix

These cases use synthetic distances injected at the existing match-proposal-to-estimator boundary, at 10:00 IST. They verify tariff and economic handling deterministically; provider labels below identify the test inputs and are not proof that a public road service returned those routes. All monetary amounts are exact to paise; A/B are canonical passenger ordering.

| Scenario | A solo km / fare | B solo km / fare | Shared km / fare | A contribution | B contribution | Combined solo | Savings (cost if negative) | Class | Composite accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Same pickup and destination (equal route distances) | 5.000 / ₹109.65 | 5.000 / ₹109.65 | 5.000 / ₹109.65 | ₹54.83 | ₹54.82 | ₹219.30 | ₹109.65 | POSITIVE | ROAD_ROUTE |
| Nearby pickups, same destination | 5.000 / ₹109.65 | 5.000 / ₹109.65 | 5.200 / ₹114.03 | ₹57.02 | ₹57.01 | ₹219.30 | ₹105.27 | POSITIVE | ROAD_ROUTE |
| Same pickup, nearby destinations | 5.000 / ₹109.65 | 5.100 / ₹111.84 | 5.200 / ₹114.03 | ₹56.45 | ₹57.58 | ₹221.49 | ₹107.46 | POSITIVE | ROAD_ROUTE |
| Nearby pickups and destinations | 5.000 / ₹109.65 | 5.100 / ₹111.84 | 6.000 / ₹131.55 | ₹65.12 | ₹66.43 | ₹221.49 | ₹89.94 | POSITIVE | ROAD_ROUTE |
| Far destinations, calibrated fallback | 5.000 / ₹109.65 | 7.000 / ₹153.45 | 20.000 / ₹438.15 | ₹182.60 | ₹255.55 | ₹263.10 | ₹175.05 additional cost | NEGATIVE | CALIBRATED_FALLBACK |
| Shared trip route estimate shorter than sum of solo estimates | 10.000 / ₹219.15 | 10.000 / ₹219.15 | 12.000 / ₹262.95 | ₹131.48 | ₹131.47 | ₹438.30 | ₹175.35 | POSITIVE | MATRIX_SCREENING |
| Equal shared and combined solo estimates | 3.000 / ₹65.85 | 3.000 / ₹65.85 | 6.007 / ₹131.70 | ₹65.85 | ₹65.85 | ₹131.70 | ₹0.00 | BREAK_EVEN | ROAD_ROUTE |
| Shared estimate more expensive | 5.000 / ₹109.65 | 5.000 / ₹109.65 | 12.000 / ₹262.95 | ₹131.48 | ₹131.47 | ₹219.30 | ₹43.65 additional cost | NEGATIVE | ROAD_ROUTE |

The fixture set covers same and nearby origin/destination patterns, far destinations, positive/equal/negative economics, and matrix/fallback/road route source combinations. A separate coordinate-sensitive routing-provider test uses synthetic Mumbai coordinates and confirms the provider receives the actual four coordinates in the expected order; changing only B's destination changes the shared and B direct distances while A's direct distance remains unchanged. `test_matching_algorithms.py` checks all six precedence-valid permutations and confirms only four contain a shared onboard segment. Actual screenshot coordinates and direct route metres were not available, so the screenshot fare values are not presented as a fully reproducible coordinate fixture.

For the separate 00:00 tariff-boundary scenario, distances are A 1,500 m, B 1,560 m, shared 3,066 m. DAY amounts are ₹33.00, ₹34.31, and ₹67.30 (₹0.01 lower combined total: break-even under tolerance); NIGHT amounts are ₹41.25, ₹42.89, and ₹84.12 (₹0.02 lower shared total: positive). The classification is conditional. Before bilateral consent, neither scenario's allocation is returned; after consent, each tariff scenario is returned independently.

## Privacy and frontend behavior

The existing DEC-013 policy remains in force. Without current affirmative consent from both proposal participants, the API omits all exact contribution and passenger-specific savings values. It also never serializes the co-passenger's solo baseline, solo fare, solo distance, or savings. The aggregate classification and nonnumeric explanation are returned without combined-solo or combined-savings amounts, avoiding direct reconstruction from the viewer's solo baseline. Bilateral consent remains tied to the current proposal/fare snapshot and the approved inference notice; revocation suppresses disclosure.

With bilateral consent, the viewer can see both proportional contributions and only their own savings/percentage. Conditional day/night tariffs return separate scenario contributions and the viewer's own scenario savings, not a midpoint split. The UI labels the shared amount as the **total taxi trip estimate**, the solo amount as **your separate solo trip estimate**, and explicitly states the shared fare is not the viewer's contribution. A distinct economic panel says whether the estimate is lower overall, approximately break-even, negative, or tariff-dependent. This keeps economic attractiveness distinct from match validity.

Component tests verify the negative warning, fare labels, conditional tariff state, consent-gated allocation, and day/night rendering. These frontend tests use controlled API fixtures, not live hosted proposals.

## Files changed for this investigation

- `backend/app/fares/allocation.py` — authoritative backend economic classification and consent-gated scenario calculations; corrected stale consent docstring.
- `backend/app/api/v1/endpoints/matching.py`, `backend/app/schemas/matching.py` — consent-gated day/night allocation response and privacy-safe economics.
- `backend/app/tests/test_fares.py`, `backend/app/tests/test_matching_algorithms.py` — controlled distance/fare matrix, rounding, allocation, routing-coordinate and order coverage.
- `frontend/src/features/ride-requests/MatchResults.tsx`, `frontend/src/features/ride-requests/__tests__/RideRequests.test.tsx`, `frontend/src/types/matching.ts` — clearer cost labels, warnings, and scenario disclosure rendering.
- `docs/phase_5b_fare_estimation_design.md`, `docs/04-database-api-contracts.md` — one-paise outcome classification and conditional scenario contract.
- `docs/phase5c-implementation-report.md` — corrected statement about the possible sign of individual savings under proportional allocation.
- `docs/phase5c-fare-behaviour-investigation.md` — this investigation.

No tariff, route provider, matching eligibility, schema, migration, environment file, or database record was changed as part of this investigation. No Phase 6A work was started.

## Verification

From `backend/`:

| Command | Result |
|---|---|
| `./.venv/bin/ruff check app` | Passed |
| `./.venv/bin/ruff format --check app` | Passed; 74 files formatted |
| `./.venv/bin/pytest -q app/tests/test_fares.py app/tests/test_matching_algorithms.py` | 51 passed, 0.66 s |
| `./.venv/bin/pytest -q` | 175 passed, 1 skipped, 12.70 s |

From `frontend/`:

| Command | Result |
|---|---|
| `npm test -- --run` | 32 tests passed across 7 files |
| `npm run lint` | Oxlint passed |
| `npm run typecheck` | TypeScript passed |
| `npm run build` | TypeScript build and Vite production build passed; Vite build 0.399 s |

NPM emitted a compatibility warning because installed npm 12.2.2 declares support for newer Node versions than the environment's Node 20.20.2; all requested frontend commands nevertheless exited successfully.

The single sandbox skip in the full backend suite is the live hosted PostGIS test, which requires database network access. The prior Phase 5C report records that isolated test passing with approved hosted connectivity and transaction rollback, but this investigation did not rerun it. No hosted authenticated two-user frontend-to-backend session was performed because authorized active account/session data was not available. Therefore hosted fare display acceptance remains unverified.

## Limitations and final status

- Original route metres and pre-paise amounts for the screenshot case are unavailable, so its route-distance cause cannot be separated from the difference between shared road routing and solo matrix screening.
- Synthetic route-distance cases validate deterministic fare, allocation, classification, and accuracy propagation; they do not establish external routing provider accuracy.
- No new tariff or routing behavior was needed or changed.
- The hosted authenticated two-user workflow was not exercised in this task. Do not treat the local test fixtures or the earlier isolated hosted PostGIS test as evidence of hosted frontend fare acceptance.

**CONDITIONAL PASS** — fare math, allocation, economic messaging, privacy serialization, frontend rendering, and local regression checks pass. Hosted authenticated frontend-to-backend acceptance remains outstanding.
