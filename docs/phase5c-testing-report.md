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
