# Phase 5B — Hosted End-to-End Verification Report

**Verification date:** 2026-11-08
**Result:** **CONDITIONAL PASS** — the hosted flow could not be completed because no authorized test-user credentials or eligible hosted requests were available. No reproducible implementation defect was established.

## Workflow performed

1. Inspected `frontend/.env.local` and `backend/.env` without printing values. Frontend Supabase URL and publishable key are configured. `VITE_API_BASE_URL` is unset, so the existing frontend default is `http://localhost:8000/api/v1`. Backend database, Supabase URL, JWKS URL, and issuer settings are configured. No test account email/password or authenticated session was configured.
2. Started the FastAPI service against its configured development environment and the Vite frontend. Both started successfully.
3. Requested `GET http://127.0.0.1:5173/` → **HTTP 200**. Requested `GET http://127.0.0.1:8000/health` → **HTTP 200**.
4. Sent an unauthenticated `POST /api/v1/ride-requests/{id}/matches` → **HTTP 401** (`Authentication credentials were not provided`). No token was supplied or fabricated.
5. Ran read-only checks against the configured hosted database: `PostGIS_Version()` succeeded; the exact candidate eligibility conditions (`ACTIVE`, departure not expired, and `expires_at` null or future) matched **0** rows; `alembic_version` was **`5b69062ab3ef`**.
6. Executed the existing parameterized PostGIS candidate-discovery `SELECT` with a transient, non-persisted probe target and Mumbai coordinates. The query completed successfully and returned **0 candidates**. No user/ride row was inserted, updated, or deleted. With no actual stored active request, this does not verify candidate matching for a valid user request.
7. Ran backend and frontend regressions. Existing ASGI matching-to-fare coverage verifies the proposal response contract and estimate generation, but uses test-injected auth, database results, and routing; it is not evidence of a live Supabase-authenticated request.
8. Stopped both local development servers.

No passwords, access tokens, publishable keys, database URLs, personal user details, or raw database rows were included in the output or this report.

## Checklist results

| Section | Result | Evidence / limitation |
|---|---|---|
| **A. Authentication** | **PARTIAL — blocked** | Supabase client configuration is present. The running API rejects unauthenticated matching with HTTP 401. A real sign-in and valid JWT acceptance could not be tested because no authorized test account/session was supplied. |
| **B. Hosted matching** | **PARTIAL — data blocked** | Hosted PostgreSQL/PostGIS connectivity and the actual candidate-discovery query were verified read-only. There are zero active, unexpired requests, so discovery returned no candidates. No two-user proposal was generated. |
| **C. Fare estimation** | **PARTIAL — hosted path blocked** | The existing matching-to-fare ASGI integration test returns shared and viewer-owned solo estimates, route provenance, and disclaimer, with candidate solo fare and Phase 5C fields absent. No hosted match existed on which to verify these fields. |
| **D. Frontend integration** | **PARTIAL — authenticated result unavailable** | Local Vite and API health returned HTTP 200; matching UI tests cover rendering, conditional ranges, loading/error/empty behavior. No authenticated browser session or hosted proposal was available to render live fare data. |
| **E. Regression and safety** | **PASS** | Backend full suite and relevant authentication/matching/fare tests pass; frontend tests pass. Hosted revision is unchanged at `5b69062ab3ef`. All hosted SQL used was read-only; no migration or data modification occurred. |

## Sanitized test evidence

- Hosted DB: `HOSTED_DB_CONNECT=ok`, `POSTGIS_AVAILABLE=True`, `ACTIVE_ELIGIBLE_REQUEST_COUNT=0`.
- Hosted candidate query: `HOSTED_POSTGIS_CANDIDATE_QUERY=executed`, `CANDIDATE_COUNT=0`; exact eligible request count is also 0.
- Hosted schema marker: `HOSTED_ALEMBIC_REVISION=5b69062ab3ef`.
- Local service checks: frontend HTTP 200; backend health HTTP 200; unauthenticated match-discovery HTTP 401.
- Backend suite: `154 passed, 1 skipped`.
- Relevant backend subset: `83 passed`.
- Frontend suite: `7 files, 30 tests passed`.

## Defects and severity

No application defect was established. The blocking conditions are test-environment inputs: no authorized test-user credentials/session and no active, unexpired hosted ride requests. The zero-candidate result is consistent with the observed empty eligible dataset and is not evidence of a matching defect.

The installed npm 12.2.2 reports that Node 20.20.2 is outside its declared supported versions. Frontend tests and build pass; this is a tooling compatibility warning, not a confirmed Phase 5B defect.

## Database and phase boundary

No migration was created or applied. No destructive or modifying database operation was run. No Phase 5C allocation, contribution, savings, consent, or disclosure work was started. Phase 6A was not started.

## Remaining action to complete hosted acceptance

An authorized operator must provision or identify two development Supabase users and create/authorize compatible active ride requests for them. Credentials or sessions must be supplied through an approved secure mechanism, not in this report. Then repeat the frontend sign-in, JWT-backed API call, hosted candidate match, and fare rendering steps.

## Final verdict

**CONDITIONAL PASS** — hosted dependencies and query execution are available, but no authorized users or eligible ride requests were available to complete the authenticated matching and fare display workflow. No implementation defect was found.
