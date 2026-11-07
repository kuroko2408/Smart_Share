# Phase 4B implementation report — remediation

**Verdict: CONDITIONAL PASS.** The implementation, regression suite, OSRM adapter, and local service startup are verified. The mandatory authenticated frontend-to-hosted-database workflow remains unverified because the development database currently has no active ride requests and no test-user credentials/session were supplied. No test accounts or credentials were invented.

## Design decisions and corrections

- Direction difference ≤45° is preferred. A difference >45° through 90° is accepted only when destinations are within 3 km. Above 90° is incompatible even if the destinations are nearby.
- Four passengers is a hard pair eligibility limit. Seat count does not add ranking points.
- Departure intervals use closed intersection semantics. A boundary-only overlap is valid at that exact instant and scores lower than a positive overlap.
- All six precedence-valid pairwise stop orders are enumerated; orders where the passengers never overlap onboard are rejected. Each passenger’s direct duration is subtracted from their own shared ride duration, and a sequence is rejected if either personal tolerance is exceeded.
- Weights are pickup 30%, destination/direction 30%, departure compatibility 20%, and individual detour 20%. Hard eligibility filters run before ranking; a score cannot make an infeasible route eligible.
- Proposals remain transient. GET recomputes current results, deterministic IDs represent unordered request pairs, and cancellation/expiry removes availability on the next request. No migration was justified. Proposal detail still requires the owned `request_id` query parameter and only resolves while the proposal remains in the recomputed top five.

## Architecture and routing

The backend keeps PostGIS candidate discovery, inexpensive direction checks, route sequence evaluation, scoring/ranking, and API response mapping in separate modules. The UI adds match discovery to active ride-request cards and renders loading, error, empty, ranked, explanation, stop sequence and routing-accuracy states. Matching does not accept a proposal, create a ride group, or change request status.

Routing uses OpenRouteService when `ROUTING_API_KEY` is supplied. Otherwise the default is the credential-free OSRM table endpoint configured by `OSRM_BASE_URL`. Requests are asynchronous, timeout-bounded, limited to four route points and spaced by at least 1.05 seconds per backend process. OSRM fastest-road-network durations are used for per-passenger detour calculations. The shared stop-sequence distance remains approximate, and OSRM duration is not live-traffic-aware. Provider failures, rate limits, no-route responses and incomplete matrices fall back to geodesic × 1.40 at a fixed 22 km/h, with explicit approximate metadata.

One real adapter request for BKC `(19.0657, 72.8687)` to Powai `(19.1176, 72.9060)` returned **645.1 seconds and 8,803.9 metres**, marked road-network duration and distance. The OSRM public demo is best-effort, for reasonable noncommercial use, and has no uptime guarantee; its stated policy is no more than one request per second. See [OSRM Table API](https://project-osrm.org/docs/v5.24.0/api/#table-service) and [demo-server policy](https://github.com/Project-OSRM/osrm-backend/wiki/Demo-server). For reliable production service, use a managed/private routing instance or another supported provider.

## Database and query-plan verification

No migration was added or applied. The hosted database remains at Alembic revision `5b69062ab3ef` (PostgreSQL 17.11 with PostGIS). Read-only inspection found the existing index definition `CREATE INDEX idx_ride_requests_pickup_gist ON public.ride_requests USING gist (pickup_location)`.

The bound query uses `ST_DWithin(b.pickup_location, ST_GeogFromText(:a_pickup_wkt), :radius_m)`. Both operands are geography; API `(latitude, longitude)` is serialized as WKT `POINT(longitude latitude)`. This predicate is GiST compatible. Read-only `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` showed:

- Full candidate query: `idx_ride_requests_active_departure` and `pk_profiles`; 0.308 ms execution, 4 shared buffers hit, 0 read. The GiST predicate appears as a filter after the temporal index scan.
- Temporal-only comparison: `idx_ride_requests_active_departure`; 0.030 ms, 1 shared buffer hit.
- Spatial-only comparison: `idx_ride_requests_pickup_gist` with an index condition on the expanded geography bounding box and a recheck using `ST_DWithin`; 94.774 ms, 129 shared buffers hit, 0 read.

The hosted table has only two ride requests and zero active requests. The planner’s use of the temporal B-tree for the full query is reasonable at that size; forcing the GiST index would be incorrect. The spatial-only plan confirms that the predicate can use the existing GiST index. Realistic large-volume Mumbai performance remains unmeasured: Docker access to the local PostGIS test image was denied by the environment, and the hosted dataset was intentionally not modified.

## API and response

- `POST /api/v1/ride-requests/{request_id}/matches` discovers and ranks current proposals for the authenticated owner.
- `GET /api/v1/ride-requests/{request_id}/matches` recomputes current proposals.
- `GET /api/v1/matches/{proposal_id}?request_id={owned_request_id}` reconstructs one current proposal.

All responses use `{ "data": ..., "message": ... }`. Proposals include the candidate journey summary, normalized component and total scores, shared departure interval, ordered stop sequence, each passenger’s estimated detour, explanations, and `is_route_approximate`, `distance_is_approximate`, `routing_accuracy`, and notice metadata. Candidate contact/auth information is not included.

Example route metadata:

```json
{
  "is_route_approximate": false,
  "distance_is_approximate": true,
  "routing_accuracy": "road_network_duration_geographic_distance",
  "routing_notice": "Road-network duration ... not live traffic predictions. Distance is estimated geographically ..."
}
```

## Files changed

Created: `backend/app/api/v1/endpoints/matching.py`; `backend/app/matching/{candidate_discovery,detour,geometry,scoring,service}.py`; `backend/app/routing/{base,fallback,ors_provider,osrm_provider,provider_factory}.py`; `backend/app/schemas/matching.py`; `backend/app/tests/test_matching_algorithms.py`; `frontend/src/features/ride-requests/MatchResults.tsx`; `frontend/src/types/matching.ts`; and the Phase 4B algorithm, implementation, testing and remediation reports.

Modified: `backend/.env.example`, `backend/pyproject.toml`, `backend/app/api/v1/router.py`, `backend/app/core/config.py`, `backend/app/tests/{conftest,test_api_v1,test_app,test_auth}.py`, `docs/06-developer-guide.md`, `frontend/src/features/ride-requests/{RideRequestCard,RideRequestList}.tsx`, `frontend/src/features/ride-requests/__tests__/RideRequests.test.tsx`, and `frontend/src/services/ride-requests.ts`. No files were deleted. The supplied `.env` and `.env.local` were not modified and remain ignored by Git.

## Verification and remaining limitations

The backend suite passes **90 tests**; frontend passes **26 tests**, lint, type check and production build. See [phase4b-testing-report.md](phase4b-testing-report.md) for commands, timings, security coverage and what remains unverified.

FastAPI and Vite were started together against the configured development environment. Backend health and the served Vite application returned HTTP 200. The frontend API base is `http://localhost:8000/api/v1`; Supabase URL and publishable-key variables are configured. This was a startup/configuration check only; no authenticated browser interaction was completed.

The actual hosted end-to-end test is blocked by missing test access and data: the hosted database contains zero active ride requests, and the supplied environment contains project configuration but no Supabase user credentials or authenticated browser session. The required owner action is to provision two development Supabase users and make two compatible active requests through the application (or provide approved test sessions); then the authenticated UI flow can be exercised. No passwords, tokens, request rows or auth records were created or changed. The public OSRM demo and realistic production-scale query performance also remain operational limitations.

**Final verdict: CONDITIONAL PASS — core remediation is implemented and regression-verified; hosted authenticated acceptance remains pending test-user and request provisioning.**
