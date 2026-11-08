# Phase 5B Fare Estimation — Integration Report

## Matching/API integration

Fare estimation is invoked from the existing `MatchProposal` response serializer. That serializer is used by match discovery and proposal detail, so the fare reflects the current proposal's route distance, including an enriched shared road route where available. It does not change candidate discovery, route choice, detour feasibility, request state, or match status.

The authenticated request owner receives:

- `fare_estimate.shared_journey`: pooled vehicle route fare, distance source, accuracy tier, surcharge status/range, and paise/rupee values.
- `fare_estimate.your_solo_baseline`: only that owner's direct-route fare estimate with the same provenance and surcharge metadata.
- `composite_accuracy`, tariff model/version, pulse strategy, excluded charges, and the no-meter-equivalence disclaimer.

The candidate's solo fare is not returned. No contribution, allocation, savings, or savings percentage is calculated or serialized. A schema inspection and API serialization test confirmed the Phase 5C fields are absent. Existing shared route, ordered stop sequence, candidate summary, and detour information remain in the response.

The complete response object is created under the existing API response envelope. Discovery remains an on-demand result; no fare or proposal persistence was added. An unsupported route source or invalid fare input logs the proposal ID and exception type and returns a null fare estimate without turning a feasible match into an API error.

## Frontend integration

The existing MatchResults workflow renders the shared journey and viewer-owned solo baseline estimate, selected pulse mode, each component's accuracy tier, conditional day/night range, exclusions, and estimate disclaimer. Road distance labels identify road-network routes; matrix and fallback distances are labelled as estimates. Loading, empty, and error behavior is retained from the existing matching workflow. The product still presents a proposal, not an accepted group.

## Authentication and ownership

The API continues to use the existing verified Supabase JWT dependency and owned-active-request guard. The integration test sent an ASGI request through the real matching route with a test principal injected by the test harness. It verified the API response produced by matching and fare estimation, but did not verify the hosted Supabase JWT/JWKS exchange.

## Database and migrations

No database persistence is needed for fare configuration or quotes. The in-memory immutable tariff registry avoids a migration. No migration or hosted database operation was performed. The last revision visible in the checked-in migration source is `5b69062ab3ef`; this report does not assert a live hosted revision check.

## Hosted end-to-end status

**Not verified.** No authenticated development account credentials or account provisioning action were supplied for this implementation turn, and no live hosted workflow was run. In particular, we did not demonstrate browser sign-in, an actual ES256 JWT through the deployed/configured backend, two active requests from separate hosted users, PostGIS candidate discovery, or rendered results from the hosted database. No credentials were invented or exposed. A Product Owner/development operator must provide or provision two development accounts and authorize the hosted test window before this evidence can be collected.

## Acceptance assessment

The implementation-level integration criterion is met in the deterministic ASGI test: a matching proposal returned by the existing pipeline contains a computed fare estimate and preserves the Phase 5C privacy boundary. Full hosted acceptance remains conditional on the live authenticated workflow described above.
