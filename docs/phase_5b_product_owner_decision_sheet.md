# Smart Share — Phase 5B/5C Product Owner Decision Sheet

**Prepared:** 8 November 2026
**Purpose:** Record the F-01 policy direction, DEC-013 approval, and implementation sequencing.
**Status:** F-01 recorded; DEC-013 approved by Product Owner on 2026-11-08. Phase 5C implementation is authorized by the subsequent Phase 5C implementation request.

## 1. F-01 — Pre-trip fare calculation and physical meter behavior

### Product Owner decision recorded

- **Approved default:** Continuous Linear Integration is the default method for pre-trip fare estimation.
- **Unresolved:** Actual electronic taxi-meter pulse quantization is configurable but legally unresolved. Ceiling, Floor, and Continuous are calculation modes; only Continuous is the selected pre-trip default. The selection does not establish how the physical meter operates.
- **Required representation:** The UI and API must label outputs as **pre-trip fare estimates**, distinguish them from final meter charges, and never claim that continuous calculation reproduces the physical taxi meter exactly.
- **Final amount:** The physical taxi meter at trip completion determines the final meter charge. Actual distance, meter behavior, waiting, traffic, tolls, parking, and other applicable charges can make the final amount differ from the estimate.

**Register status:** DEC-004 approved for the pre-trip estimate policy. The legal/metrological question remains open and is a documented limitation, not a reason to block an accurately labeled estimate engine.

## 2. DEC-013 — Exact co-passenger contribution disclosure

### Approved Product Owner decision

Approve exact proportional co-passenger contribution display for shared-cost transparency, subject to the disclosure and consent controls below. This policy has a residual economic-privacy risk: given a viewer’s own solo baseline fare and exact share, the viewer can algebraically infer the co-passenger’s solo baseline from the exact contribution (approximately `F_B = F_A × S_B / S_A`). The audit example estimates the inference to within about two paise. Consent informs participants about this risk; it does not eliminate it.

### Required transparency and consent controls

1. Show a concise, plain-language notice immediately beside the exact contribution, before either participant views or confirms an exact split. State that the other participant can use the amount and their own fare information to estimate their solo baseline.
2. Obtain separate, affirmative, participant-specific consent from both people before returning or displaying exact split values. Each participant must consent to disclosure of their own contribution to the co-passenger. A participant’s consent cannot authorize disclosure of the other person’s amount.
3. Do not infer consent from silence, account creation, general terms, or a default-enabled control. Provide an equally clear decline action. A decline or withdrawal before confirmation prevents exact contribution disclosure and follows the approved alternative or exits the shared-cost flow.
4. Record the consent text/version, participant, timestamp, and selected disclosure mode through an approved auditable mechanism. Do not assume a database field or migration exists; if the current architecture lacks a suitable mechanism, document a proposed additive design for separate review before changing schema.
5. Keep the co-passenger’s direct solo baseline fare, private savings, solo distance, and private solo route geometry/waypoints redacted. Shared pickup/drop-off and pooled itinerary details needed to assess the proposed shared ride remain purpose-limited trip information and must not be presented as permission to reveal solo-route information.

### Alternative if exact disclosure is rejected

Use bucketed contributions, initially proposed as nearest ₹10, as a lower-precision policy. Bucketing alone does not guarantee privacy: an exact shared total combined with an exact own share reconstructs the hidden contribution. Any bucketed contract must review and, where necessary, coarsen or withhold linked amounts while preserving understandable cost accounting. Do not claim that bucketing eliminates inference.

**Decision:** Approve exact disclosure with bilateral consent and inference notice.

**Approval recorded:** 2026-11-08, via the Product Owner's explicit answer. Exact display remains unavailable until both participants separately consent to the current notice. The approved controls and redactions remain mandatory.

## 3. Remaining risks

- Physical meter pulse behavior remains legally unresolved. Continuous is an estimate policy, not an assertion of meter equivalence.
- Pre-trip estimates can differ from final charges due to actual route/distance, pulse behavior, traffic or waiting time, tolls, parking, and tariff changes.
- Exact contribution disclosure leaves residual solo-baseline inference risk even after informed consent.
- Candidate/shared itinerary information may support location or travel-pattern inference; private solo route details and economics must remain redacted.
- A bucketed fallback reduces displayed precision but may be algebraically defeated by exact linked amounts.
- Consent must be available to both participants and reliably enforced by the API. Phase 5C implements append-only consent events in a justified additive migration; applying that migration to a hosted database remains an environment-specific deployment step.

## 4. Phase 5B implementation acceptance criteria

Phase 5B was authorized for implementation on 2026-11-08. It is limited to fare estimation; Phase 5C adds allocation/disclosure under the separately approved decision below. The Phase 5B report records a conditional result because the live hosted workflow remains unverified.

1. A versioned fare model calculates configured shared-journey and solo-baseline estimates from validated Phase 5A normalized route metrics.
2. Continuous Linear Integration is the default for pre-trip estimates. Other pulse modes may remain configurable for comparison, but no mode may be described as verified physical meter behavior without authoritative evidence.
3. Every API/UI amount is labeled as a pre-trip estimate and is clearly distinct from the final physical meter charge. No exact meter-reproduction claim is made.
4. Tariff arithmetic uses Decimal and exact paise serialization; statutory tariff rounding, currency, effective date, timezone, surcharge boundaries, and conditional departure-window ranges follow the accepted specification.
5. Route provenance uses the conservative weakest-material-input rule. Provider/fallback errors are handled, and low-accuracy estimates are clearly identified rather than overstated.
6. Toll, waiting, parking, and other excluded amounts are disclosed. The estimate must not represent excluded charges as included or final.
7. Public responses are viewer-scoped. They do not expose a co-passenger contribution, co-passenger solo baseline, private savings, solo distance, or private solo route geometry/waypoints. Any internal values required downstream are not serialized to another participant.
8. Fare calculation does not alter match eligibility, proposal lifecycle, request status, or Phase 5A route metrics. Existing matching/authentication/request behavior remains regression-tested.
9. Unit, boundary, property, authorization, provenance, provider-failure, API, and frontend tests cover the approved design. Any schema/migration need is justified and reviewed separately before application.
10. Implementation report includes actual commands/results, response examples, accuracy caveats, migration status, and known limitations. No Phase 5C behavior is claimed complete.

## 5. Phase 5C and Phase 6A dependency recommendations

### Phase 5C — Fare allocation and savings

The Phase 5A routing architecture names Phase 5C as allocation scope; DEC-008 in this decision register and Sections 9–12 of the Phase 5B design define its authoritative formula and privacy contract. It consumes Phase 5A normalized routing outputs through Phase 5B fare estimates. The fare-output contract is implemented and stable, while Phase 5B hosted acceptance remains pending. DEC-013 is approved for exact contribution output only with bilateral consent. Phase 5C acceptance includes sum conservation, fairness/dissavings behavior, per-viewer privacy, consent enforcement, and hosted integration evidence.

### Phase 6A — Fare estimate, allocation, and consent UX

No Phase 6A definition existed in the repository before the roadmap amendment. Phase 6A covers broader frontend presentation of estimates, allocation, transparency notices, and consent controls. It depends on stable Phase 5B/5C API contracts; DEC-013 is now resolved. UI/API-backed acceptance should follow Phase 5C API acceptance. The minimal consent controls required to gate Phase 5C output are included in Phase 5C implementation.

### Recommended sequence

**Phase 5A (complete) → Phase 5B estimator contract (implemented; hosted acceptance pending) → Phase 5C allocation implementation (authorized after DEC-013 approval; hosted acceptance pending) → Phase 6A broader integrated fare/consent UX → end-to-end regression acceptance.** Phase 5C can be implemented against the stable existing fare contract, but deployment acceptance remains contingent on hosted migration and integration evidence. Phase 6A must use the bilateral consent behavior and never bypass it.

## 6. Related documents updated

- [Phase 5B/5C decision register](phase_5b_fare_model_decisions.md)
- [Phase 5B fare-estimation design and Phase 5C interface](phase_5b_fare_estimation_design.md)
- [Phase 5B/5C risk analysis](phase_5b_fare_estimation_risk_analysis.md)
- [Phase 5B/5C/6A test strategy](phase_5b_fare_estimation_test_strategy.md)
- [Revised Phase 5B pre-implementation audit](phase_5b_final_pre_implementation_audit.md)
- [Project roadmap](05-roadmap.md)

**Implementation authorization:** Phase 5B was authorized on 2026-11-08; DEC-013 exact disclosure was approved on 2026-11-08 subject to bilateral consent; Phase 5C was subsequently authorized by the Product Owner. Phase 6A remains outside the present implementation.
