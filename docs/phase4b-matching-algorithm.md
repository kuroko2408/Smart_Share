# Phase 4B matching algorithm and API

## Current proposal lifecycle

Discovery is computed on demand and stored only for the duration of the HTTP response. No match tables or migrations are added. `GET /ride-requests/{request_id}/matches` recomputes results, so request changes and cancellations naturally affect the next response. Proposal IDs are deterministic UUIDv5 values derived from the unordered request pair; they are identifiers for a recomputable suggestion, not durable records. The detail route currently requires `request_id` as a query parameter to establish ownership and reconstruct the proposal. This is a deliberate MVP limitation: standalone durable proposal URLs require persisted snapshots and stale-record invalidation.

## Eligibility and filtering

1. The authenticated owner’s request must be `ACTIVE` and not expired.
2. A parameterized PostGIS query selects at most 20 other users’ requests. It filters `ACTIVE`, unexpired departure windows, overlapping departure intervals, a maximum 2,000 metre pickup radius, and total seats at or below four. Geography values are constructed from API latitude/longitude as `POINT(longitude latitude)`. The pickup condition is `ST_DWithin(geography, ST_GeogFromText(:wkt), :radius_m)` and is compatible with the existing GiST geography index.
3. Initial bearings use the forward geodesic formula. A difference up to 45° is preferred; 45°–90° is borderline and allowed only when destinations are within 3 km; above 90° is rejected even for nearby destinations.
4. Departure overlap is the closed interval intersection. A boundary-only intersection is permitted but naturally receives a low temporal score.
5. A bounded routing call evaluates the four points. All six precedence-valid stop sequences are enumerated. A sequence is eligible only if both passengers are onboard together for at least one segment, each pickup precedes its own dropoff, and each personal detour stays within their own tolerance. This rejects the two mathematically precedence-valid orders where the first passenger is dropped before the second is picked up. Each passenger’s ride time is measured from their pickup to their own dropoff; its direct route time is subtracted.

## Ranking

Scores are normalized to `[0, 1]`: pickup proximity 30%, destination similarity/direction 30%, temporal overlap and midpoint difference 20%, and individual detour headroom 20%. The vehicle capacity is a hard eligibility gate and does not contribute a score. Results sort by score descending, total detour ascending, and pickup distance ascending, with at most five proposals returned.

`ROUTING_API_KEY` selects OpenRouteService when configured. Without that credential, the default provider is the public OSRM table API at `OSRM_BASE_URL` (default `https://router.project-osrm.org`). The adapter makes asynchronous requests, enforces a process-wide minimum 1.05 second spacing, bounds each request to four points, and uses `ROUTING_TIMEOUT_SECONDS` (default 5 seconds). It requests fastest-road-network durations and distances; the matching pipeline uses road-network durations for detour checks, but shared-route distance remains a geographic approximation. Results say that routing is not live traffic-aware. The public OSRM demo is best-effort, intended for reasonable noncommercial usage, and has no uptime guarantee; the project policy says not to exceed one request per second. See [OSRM Table API](https://project-osrm.org/docs/v5.24.0/api/#table-service) and [OSRM demo-server policy](https://github.com/Project-OSRM/osrm-backend/wiki/Demo-server).

If OSRM times out, rate-limits, returns no route or an incomplete matrix, the engine uses the existing fallback and labels it approximate. Fallback estimates use geodesic distance × 1.40 and a fixed 22 km/h. They do not model Mumbai road topology, bridges, one-way systems or current traffic, and must not be represented as verified road journeys. The fallback remains configurable with `ROUTING_PROVIDER=fallback`. For sustained usage, configure a supported provider or run a managed/private OSRM instance instead of relying on the public demo server.

## Endpoints

- `POST /api/v1/ride-requests/{request_id}/matches`: authenticate, verify ownership and active status, discover, score and return proposals.
- `GET /api/v1/ride-requests/{request_id}/matches`: recompute currently valid suggestions for the owner.
- `GET /api/v1/matches/{proposal_id}?request_id={owned_request_id}`: recompute and return the matching proposal if it remains in the top five.

Responses follow the standard `{ "data": ..., "message": ... }` API envelope. The data contains the candidate’s display name and journey coordinates/labels, scores, explanation strings, shared interval, ordered stops, per-passenger detours, estimated duration/distance and accuracy metadata (`routing_accuracy`, `is_route_approximate`, and `distance_is_approximate`). It omits contact and auth details. Proposals never change a request to `MATCHED` and do not form a group.

Example (abbreviated):

```json
{
  "target_request_id": "<request UUID>",
  "total_candidates_found": 1,
  "proposals": [{
    "proposal_id": "<deterministic proposal UUID>",
    "candidate": {
      "candidate_display_name": "Rider",
      "pickup_distance_meters": 430,
      "estimated_detour_minutes_target": 4.2,
      "estimated_detour_minutes_candidate": 2.1,
      "scores": {"composite_score": 0.84}
    },
    "best_sequence": "PA→PB→DA→DB",
    "is_route_approximate": true,
    "routing_notice": "Route duration estimated using spatial corridor baseline...",
    "compatibility_explanations": ["Pickup points are 430 metres apart."]
  }]
}
```

## Routing configuration

`ROUTING_API_KEY` enables the OpenRouteService adapter. With no key, OSRM is used by default. `OSRM_BASE_URL` can point to an OSRM-compatible deployment; it requires no credential. `ROUTING_TIMEOUT_SECONDS` controls provider timeouts (default 5 seconds). `ROUTING_PROVIDER=fallback` explicitly disables network routing. Provider failures use the approximate fallback. No routing credential is required for OSRM, but its public demo service is best-effort and rate-limited. The shared distance reported by the current matching pipeline remains approximate even when a provider supplies road-network duration; responses expose that distinction separately.

## Frontend

Active ride request cards expose “Find matches”. The user initiates discovery and sees loading, error, empty and ranked states. Cards show score, pickup/destination proximity, departure overlap, both detours and shared duration. Expanding “Why this suggestion?” shows the score factors, explanation strings, ordered stops and route accuracy notice. The screen states that suggestions do not create an accepted group.
