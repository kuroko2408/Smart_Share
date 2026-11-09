<<<<<<< Updated upstream
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
# Phase 5C Testing Report

**Date:** 2026-11-09 (fare behaviour regression run)  
**Verdict:** CONDITIONAL PASS — automated tests and builds pass; hosted authenticated bilateral-consent and fare workflow is not verified.

## Backend

From `backend/`:

| Command | Result | Time |
|---|---|---:|
| `./.venv/bin/ruff check app` | Passed | completed |
| `./.venv/bin/ruff format --check app` | Passed; 74 files formatted | completed |
| `./.venv/bin/pytest -q app/tests/test_fares.py app/tests/test_matching_algorithms.py` | **51 passed** | 0.66 s |
| `./.venv/bin/pytest -q` | **175 passed, 1 skipped** | 12.70 s |

Separately, after the migration was applied, `./.venv/bin/pytest -q -rs app/tests/test_matching_postgis.py` ran with approved development-database connectivity and **passed (1 test, 0.49 s)**. It uses a transaction and rolls back its synthetic requests. The full sandboxed suite still reports that test as skipped because the sandbox cannot reach hosted PostGIS.

The single skipped test is `app/tests/test_matching_postgis.py:48`: “Hosted PostGIS database is unreachable or network is restricted in current sandbox.” No tests were skipped to hide failures. New coverage includes deterministic route-to-fare scenarios for positive, break-even and negative economics; integer-paise conservation and residual rounding; the supplied ₹283.27/₹276.57 negative case; individual savings-sign invariants under proportional allocation; conditional day/night classifications; coordinate-sensitive route construction; bilateral-only schema output; consent snapshot freshness; append-only grant/revoke event data; and absence of fare values from the audit model. API regressions also verify that missing authentication is rejected on both consent routes and another user cannot grant or revoke consent for an owned request.

An initial regression run surfaced three existing API tests whose bare `AsyncMock` sessions did not model SQLAlchemy's synchronous `Result.scalars()` interface. The fixture now returns an empty scalar result for the newly introduced consent lookup. Assertions were updated to distinguish a disclosure notice from actual allocation fields: no contribution or savings amounts are present before consent. The full suite then passed.

## Frontend

From `frontend/`:

| Command | Result | Time |
|---|---|---:|
| `npm test -- --run` | **7 files, 32 tests passed** | 3.48 s |
| `npm run lint` | Oxlint passed | completed |
| `npm run typecheck` | TypeScript passed | completed |
| `npm run build` | TypeScript build and Vite production build passed | 0.39 s Vite build |

The consent UI test verifies the inference notice appears, amounts remain hidden before bilateral consent, and exact contribution display appears only after the consent API action and a refreshed response show both participants active. Fare behavior tests also verify the economic warning, distinguish total taxi fare from own solo estimate and contribution, and render conditional day/night scenarios without presenting a misleading midpoint allocation. Existing empty, loading, error, matching, and route rendering tests remain passing.

NPM printed an environment warning: npm 12.2.2 does not support the installed Node 20.20.2 version. The commands nevertheless completed successfully.

## Migration verification

`./.venv/bin/alembic upgrade 5b69062ab3ef:c5d013c0a501 --sql` generated SQL creating only `match_disclosure_consent_events`, its two application foreign keys, two check constraints, and one composite index, then advancing the Alembic version. The existing migration was then applied to the verified development database. Read-only verification confirmed the table columns/constraints/index and Alembic revision `c5d013c0a501`; the audit table contained zero events immediately after migration. No existing application rows or Supabase-managed schemas were modified.

## Remaining verification

- No two authorized development accounts or authenticated sessions were available for bilateral consent persistence testing.
- The full sandboxed suite cannot reach hosted PostGIS, although the isolated live PostGIS integration test passed separately with approved network access.
- Frontend integration used mocked API responses in automated component tests; it is not evidence of hosted end-to-end operation.

Therefore the automated test/build gates and migration deployment pass, but full Phase 5C acceptance remains conditional on authenticated two-user integration verification.
<<<<<<< Updated upstream
=======
=======
# Phase 5C Fare Allocation — Testing Report

**Status:** Complete  
**Date:** November 9, 2026  
**Test Suite:** Backend Pytest (`backend/app/tests/test_fares.py`, `backend/app/tests/test_matching_phase5a.py`), Frontend Vitest (`frontend/src/features/ride-requests/__tests__/RideRequests.test.tsx`)

---

## 1. Mathematical and Financial Invariants Verification

The Phase 5C allocation engine enforces 12 core mathematical and financial invariants, verified by automated unit tests:

| Invariant # | Description | Test Function | Test Outcome |
| :--- | :--- | :--- | :--- |
| **INV-1** | Contributions are non-negative ($S_A \ge 0, S_B \ge 0$). | `test_allocation_invariants_and_proportional_weighting` | **PASS** |
| **INV-2** | Exact sum conservation: $S_A + S_B \equiv F_{\text{shared}}$ in paise and Decimal. | `test_allocation_invariants_and_proportional_weighting` | **PASS** |
| **INV-3** | Proportional weighting: $F_A > F_B \implies S_A > S_B$. | `test_allocation_invariants_and_proportional_weighting` | **PASS** |
| **INV-4** | When $F_{\text{shared}} < F_A + F_B$, both passengers save money. | `test_allocation_invariants_and_proportional_weighting` | **PASS** |
| **INV-5** | When $F_{\text{shared}} == F_A + F_B$, `BREAK_EVEN` is reported and no savings are claimed. | `test_allocation_break_even_outcome` | **PASS** |
| **INV-6** | When $F_{\text{shared}} > F_A + F_B$, `UNATTRACTIVE` is reported with negative savings. | `test_allocation_dissavings_outcome` | **PASS** |
| **INV-7** | No fabricated savings in break-even or dissavings (`is_saving = False`, `savings_percent = 0.0`). | `test_allocation_dissavings_outcome` | **PASS** |
| **INV-8** | Rounding cannot create false savings claim in micro-fare edge cases. | `test_allocation_rounding_cannot_create_false_savings` | **PASS** |
| **INV-9** | Solo baseline estimates remain unchanged by allocation. | `test_allocation_invariants_and_proportional_weighting` | **PASS** |
| **INV-10** | Original shared trip fare remains unchanged by allocation. | `test_allocation_invariants_and_proportional_weighting` | **PASS** |
| **INV-11** | Driver's agreed gross fare is never reduced or discounted. | `test_allocation_invariants_and_proportional_weighting` | **PASS** |
| **INV-12** | Safe handling of negative, zero, and micro-fare inputs without exceptions or division errors. | `test_allocation_zero_and_invalid_inputs` | **PASS** |

---

## 2. Privacy & DEC-013 Consent Verification

| Test Case | Description | Test Outcome |
| :--- | :--- | :--- |
| **TEST-PRIV-01** | Co-passenger solo baseline is redacted from serialized proposal. | **PASS** |
| **TEST-PRIV-02** | Co-passenger contribution is `None` prior to bilateral consent. | **PASS** |
| **TEST-PRIV-03** | Co-passenger private savings are redacted in both unconsented and consented states. | **PASS** |
| **TEST-PRIV-04** | Bilateral consent reveals `co_passenger_contribution` such that $S_A + S_B == F_{\text{shared}}$. | **PASS** |

---

## 3. Frontend Presentation Verification

| Test Case | Component | Verification Goal | Outcome |
| :--- | :--- | :--- | :--- |
| **FE-ALLOC-01** | `MatchResults.tsx` | Clearly distinguishes Original shared fare, Solo baseline, and Allocated share. | **PASS** |
| **FE-ALLOC-02** | `MatchResults.tsx` | Renders savings badge and percentage savings when beneficial. | **PASS** |
| **FE-ALLOC-03** | `MatchResults.tsx` | Displays DEC-013 privacy notice and driver gross fare conservation. | **PASS** |

---

## 4. Test Execution Summary

```
backend/app/tests/test_fares.py: 20 passed in 0.06s
backend/app/tests/test_matching_phase5a.py: 24 passed in 0.14s
Full backend suite: 160 passed, 1 skipped in 10.21s
Frontend vitest suite: 30 passed in 1.49s
Total automated tests executed: 190 tests (100% passing)
```
>>>>>>> 3dfc1f3 (5C)
>>>>>>> Stashed changes
