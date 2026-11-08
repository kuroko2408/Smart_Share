# Smart Share — Phase 5B Final Pre-Implementation Audit Report (Revised)
## Comprehensive Technical, Mathematical, Financial, API Security, Privacy & Regulatory Audit

**Project:** Smart Share — Intelligent Cab-Pooling Platform  
**Target Geography:** Mumbai, India  
**Phase:** Phase 5B — Fare Estimation Models  
**Task:** Targeted Audit Corrections & Final Design Amendment  
**Date:** November 8, 2026  
**Auditor Roles:** Principal Software Architect, Senior Backend Engineer, Financial Calculation Auditor, API Security Reviewer, QA Architect  
**Execution Mode:** STRICTLY DOCUMENTATION ONLY — Application code, migrations, and database state unmodified  
**Implementation Authorization:** NOT GRANTED — Awaiting Product Owner review and decision approvals  

---

## 1. Executive Verdict & Sign-Off Recommendation

### **VERDICT: CONDITIONAL PASS — DEC-013 PENDING FOR PHASE 5C**

Following a rigorous, skeptical re-investigation of independent review findings, the previous blanket PASS verdict has been superseded. Phase 5B is evaluated as **CONDITIONAL PASS — DEC-013 PENDING FOR PHASE 5C**. F-01 no longer blocks the isolated estimate engine; DEC-013 remains a gate for exact cost-share disclosure and its dependent user experience.

The technical architecture, financial formulas, sum-conservation invariants, and API contracts are documented. The Product Owner has resolved the Phase 5B pre-trip estimate default (F-01). One decision remains before fare allocation disclosure can be implemented. Phase 5B fare-estimation implementation can proceed independently once separately authorized, provided it respects the scope boundary that excludes co-passenger contribution disclosure.

1. **DEC-013 / F-02 remains pending for Phase 5C exact allocation disclosure:**
   Exact proportional co-passenger contribution ($S_B$) enables inference of that passenger's solo baseline ($F_B \approx F_A \times S_B/S_A$), estimated within a few paise in the audited example. The proposed policy includes clear user-facing disclosure and separate affirmative consent from both participants. Direct solo baseline fares, savings, solo distances, and private solo-route details remain redacted. The disclosure decision remains with the Product Owner.
2. **F-01 / DEC-004 pre-trip estimate policy is approved; physical meter quantization remains unresolved:**
   The Product Owner approved Continuous Linear Integration as the default pre-trip estimation method. This does not establish whether a physical meter uses Ceiling, Floor, or continuous pulse behavior. Estimates must not claim exact meter reproduction and must be distinguished from final meter charges.

Implementation authorization remains with the Product Owner. **No runtime code has been modified in this audit pass.**

---

## 2. Finding-by-Finding Resolution Table

| Finding ID | Severity | Source Evidence Inspected | Core Issue | Resolution / Status | Implementation Blocker? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **F-01** | **HIGH** | MMRTA Tariff Notifications, Legal Metrology Rules 2011, Khatua Committee Report | Physical meter pulse quantization at partial 100m boundaries is not established. | PO approved continuous as pre-trip estimate default. Quantization remains configurable and unresolved; explicit estimate/final-charge distinction and no exact-meter claim required. | **NO for labeled Phase 5B estimates; physical meter equivalence remains unresolved** |
| **F-02** | **HIGH** | Fare allocation contract; algebraic formula $F_B \approx F_A \times S_B / S_A$ | Exact contribution reveals enough information to infer solo baseline. | DEC-013 proposes exact disclosure with residual-risk notice and bilateral consent; private economics/routes remain redacted; bucketed alternative retained. | **YES for Phase 5C exact disclosure until PO decision** |
| **F-03** | **HIGH** | `backend/app/routing/models.py`, `backend/app/matching/service.py` | Labeled composite accuracy as "Tier 1 Hybrid", violating weakest-link principle; enum names mismatched. | Corrected enum to `DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE`. Enforced conservative composite rule: aggregate is `MATRIX_SCREENING`. Retained standard 4 tiers. | **RESOLVED** (No blocker) |
| **F-04** | **MEDIUM** | Khatua Committee Report Clause 4.18.1, MMRTA notifications | Waiting charges assumed as ₹1.50/2 min without verified September 2026 rule. | Verified waiting charge formula (10% of per-km fare/min). Explicitly excluded waiting charges, tolls, and parking from pre-trip matching estimate. | **RESOLVED** (No blocker) |
| **F-05** | **LOW** | `phase_5b_fare_estimation_design.md` Section 8.3 | Divergence bound unit omitted ("percentage points") and assumptions unstated. | Corrected unit to **percentage points (pp)**. Explicitly stated conditional assumptions ($F_A, F_B \ge \text{₹}33.00$, paise quantization, sum conservation). | **RESOLVED** (No blocker) |
| **F-06** | **MEDIUM** | `backend/app/schemas/matching.py`, `Asia/Kolkata` timezone specs | Night surcharge boundaries ambiguous; UTC vs IST evaluation undefined. | Defined exact half-open interval $[00:00:00, 05:00:00)\text{ IST}$. Documented second-by-second behavior and `CONDITIONAL` range responses for overlapping departure windows. | **RESOLVED** (No blocker) |
| **F-07** | **MEDIUM** | `backend/app/routing/models.py`, `schemas/matching.py`, `matching/service.py` | Documentation used nonexistent enum names (`PROVIDER_ROUTE_TURN_BY_TURN`). | Reconfirmed exact source field names, types, and StrEnum members. Updated documentation to match actual Phase 5A source code. | **RESOLVED** (No blocker) |

---

## 3. Finding F-01 — Mumbai 100m Meter Pulse Behaviour

### 3.1 Regulatory Investigation & Status
An investigation into Maharashtra transport and metrology regulations revealed:
- **Officially Established Rules:**
  - Base fare: ₹33.00 for the first 1.50 km (1,500 meters).
  - Subsequent rate: ₹21.90 per km for distance exceeding 1,500 meters.
  - Night surcharge: 25% additional fare between 00:00 and 05:00 IST.
  - Statutory rounding: Fractions $< 50\text{ paise}$ ignored; $\ge 50\text{ paise}$ rounded up to the next integer Rupee.
  - Electronic taximeters receive electrical pulses from vehicle transmission transducers calibrated to a constant $k$ (pulses/km) under the Eighth Schedule (Part VIII) of the Legal Metrology (General) Rules, 2011.
- **Unresolved Metrological Behavior:**
  - In physical electronic meters, does entering a new 100m interval (e.g. at 1,501m) immediately increment the meter pulse (Ceiling $\lceil \cdot \rceil$), or does the meter hold the base fare until the full 100m pulse is completed at 1,600m (Floor $\lfloor \cdot \rfloor$)?
  - On printed RTO tariff cards used during recalibration transition periods, rates are tabulated at discrete 100m steps (1.5 km = ₹33, 1.6 km = ₹35, 1.7 km = ₹37). The tariff card does not define intermediate meter pulses between 1,500m and 1,600m.
  - **Status:** **UNRESOLVED**. In the absence of a primary engineering specification from an MMRTA-approved taximeter manufacturer (e.g., Sansui, Pulsar, or Geotoll meter calibration manuals), pulse quantization at fractional boundaries cannot be claimed as legally established.

### 3.2 Mandatory Boundary Analysis Across Hypotheses

The table below evaluates the 8 mandatory boundary distances across all three competing hypotheses:
- **Hypothesis 1 (Ceiling):** $n = \lceil \max(0, d - 1500) / 100 \rceil$ (Every started 100m interval).
- **Hypothesis 2 (Floor):** $n = \lfloor \max(0, d - 1500) / 100 \rfloor$ (Every completed 100m interval).
- **Hypothesis 3 (Continuous):** $F = 33.00 + (\max(0, d - 1500) / 1000) \times 21.90$ (Exact distance ratio).

```
+-----------------------------------------------------------------------------------------------------------------------------------+
|                                                 MANDATORY BOUNDARY EVALUATION                                                     |
+-------+--------+----------------------------+----------------------------+--------------------------------------------------------+
| Dist  | Excess | Hypothesis 1 (Ceiling)     | Hypothesis 2 (Floor)       | Hypothesis 3 (Continuous Linear)                       |
| (m)   | (m)    | Pulses | Day | Night Gross  | Pulses | Day | Night Gross  | Raw Subtotal | Day Meter | Night Gross | Night Meter |
+-------+--------+--------+-----+--------------+--------+-----+--------------+--------------+-----------+-------------+-------------+
| 1,499 |      0 |      0 | ₹33 | ₹41.25 (₹41) |      0 | ₹33 | ₹41.25 (₹41) |      ₹33.000 |       ₹33 |     ₹41.250 |         ₹41 |
| 1,500 |      0 |      0 | ₹33 | ₹41.25 (₹41) |      0 | ₹33 | ₹41.25 (₹41) |      ₹33.000 |       ₹33 |     ₹41.250 |         ₹41 |
| 1,501 |      1 |      1 | ₹35 | ₹43.99 (₹44) |      0 | ₹33 | ₹41.25 (₹41) |      ₹33.022 |       ₹33 |     ₹41.277 |         ₹41 |
| 1,599 |     99 |      1 | ₹35 | ₹43.99 (₹44) |      0 | ₹33 | ₹41.25 (₹41) |      ₹35.168 |       ₹35 |     ₹43.960 |         ₹44 |
| 1,600 |    100 |      1 | ₹35 | ₹43.99 (₹44) |      1 | ₹35 | ₹43.99 (₹44) |      ₹35.190 |       ₹35 |     ₹43.988 |         ₹44 |
| 1,601 |    101 |      2 | ₹37 | ₹46.73 (₹47) |      1 | ₹35 | ₹43.99 (₹44) |      ₹35.212 |       ₹35 |     ₹44.015 |         ₹44 |
| 1,699 |    199 |      2 | ₹37 | ₹46.73 (₹47) |      1 | ₹35 | ₹43.99 (₹44) |      ₹37.358 |       ₹37 |     ₹46.698 |         ₹47 |
| 1,700 |    200 |      2 | ₹37 | ₹46.73 (₹47) |      2 | ₹37 | ₹46.73 (₹47) |      ₹37.380 |       ₹37 |     ₹46.725 |         ₹47 |
+-------+--------+--------+-----+--------------+--------+-----+--------------+--------------+-----------+-------------+-------------+
```

### 3.3 Architectural Resolution & Recommendation
To prevent an unverified metrological assumption from blocking system implementation:
1. `FareModelConfig` parameterizes the pulse quantization strategy:
   `pulse_quantization_mode: Literal["CEILING", "FLOOR", "CONTINUOUS"] = "CONTINUOUS"`.
2. The Product Owner approves **Continuous Linear Integration** as the default pre-trip estimate method. This is an estimation policy and is not a finding about a physical meter's pulse behavior.
3. CEILING and FLOOR remain configurable comparison hypotheses. If a scenario range is displayed, label it as a range across assumed calculation modes, not a verified physical meter range.
4. Customer-facing copy must label amounts as **pre-trip estimates**, state that final charges are determined by the physical taxi meter at trip completion, and avoid claims of exact meter reproduction.

---

## 4. Finding F-02 — Clarify Co-Passenger Economic Privacy

### 4.1 Direct Disclosure vs Inferential Disclosure
The current Phase 4B match response exposes candidate trip endpoints for a ride decision; the proposed Phase 5C fare response has not been implemented. Under DEC-013, if approved, it would return to a consenting viewer:
  1. `your_allocated_fare` ($S_A$)
  2. `co_passenger_contribution` ($S_B$)
  3. `total_shared_fare` ($F_{\text{shared}} = S_A + S_B$)
  4. `your_solo_baseline_fare` ($F_A$)

Because the platform uses a strictly proportional cost allocation ($S_A / S_B = F_A / F_B$), any user can compute:
$$F_B^* = F_A \times \frac{S_B}{S_A}$$

### 4.2 Precision and Uncertainty of the Inferred Baseline
Due to paise rounding ($S_A = q_A \pm \epsilon_A$, with $|\epsilon_A| \le \text{₹}0.005$):
The error in the inferred solo baseline $\hat{F}_B$ is:
$$|\Delta F_B| \approx |\epsilon_A| \times \frac{(F_A + F_B)^2}{F_A F_{\text{shared}}}$$
For typical urban routes ($F_A = \text{₹}188.00, F_B = \text{₹}143.00, F_{\text{shared}} = \text{₹}223.00$):
$$|\Delta F_B| \le 0.005 \times \frac{331^2}{188 \times 223} = 0.005 \times 2.61 \approx \text{₹}0.013 \quad (\approx 1.3\text{ paise})$$
**Result:** The co-passenger's solo baseline fare can be mathematically reverse-engineered to within **$\pm 2\text{ paise}$**.

### 4.3 Repeated Observations and External Information
If a user observes multiple proposals with the same candidate or correlates the inferred fare with public tariff tables:
$$\hat{d}_{\text{solo}, B} \approx 1,500 + \frac{\hat{F}_B - 33.00}{21.90} \times 1,000\text{ meters}$$
The user can estimate the candidate's solo travel distance with high accuracy ($\pm 50\text{ meters}$).

Furthermore, Phase 5A's existing `MatchProposalSchema` contains shared-trip candidate pickup and destination points to support the ride decision. A viewer may already estimate straight-line separation from those endpoints. The exact fare disclosure can strengthen inference about solo baseline fare and, when combined with external information, travel distance. Those endpoint disclosures are not a basis for exposing private solo-road distance, route geometry, or waypoints. The DEC-013 notice must describe this residual inference risk accurately.

### 4.4 Formal Product Owner Decision Required (DEC-013)
The following decision is recorded in `docs/phase_5b_fare_model_decisions.md` and submitted for formal sign-off:

> **DEC-013: Intentional Disclosure of Co-Passenger Contribution in Proportional Allocation**  
> **Status:** PROPOSED — PENDING FINAL PRODUCT OWNER APPROVAL (Phase 5C).
> **Policy:** Display exact proportional co-passenger contribution for shared-cost transparency only after both participants separately and affirmatively consent. Explicitly disclose that the contribution, combined with a viewer's own baseline/share, permits algebraic inference of the co-passenger's solo baseline and may support further distance inference. This is a residual privacy risk; consent does not remove the inference.
> **User notice and consent:** Show the disclosure adjacent to the amount before either participant views or confirms an exact split. Do not rely on general terms or silence. Record each participant's consent version, timestamp, and disclosure mode through an approved auditable mechanism; a decline or pre-confirmation withdrawal prevents exact disclosure.
> **What Remains Strictly Private:** Direct solo baseline fares, private savings, solo road distances, and private solo-route geometry/waypoints remain redacted. Candidate endpoints and pooled itinerary details already exposed for trip evaluation are purpose-limited shared-trip data and do not authorize exposing additional solo-route details.
> **Alternative:** If exact disclosure is rejected, use the proposed nearest-₹10 bucket policy only after reviewing all linked values. Exact shared total plus exact own share can still reveal the other contribution, so linked value precision must also be reviewed; buckets do not automatically eliminate inference.

---

## 5. Finding F-03 — Correct Composite Route Accuracy

### 5.1 Conservative Aggregation Rule (Weakest-Link Principle)
The previous audit labeled Top 1 enriched proposals as "Tier 1 Hybrid". This label is ambiguous and overstates the accuracy of the total fare estimate because the solo baseline fares ($F_A$ and $F_B$) are derived from matrix table screening rather than turn-by-turn routing.

**The Conservative Aggregation Rule:**
> An aggregate estimate must not claim a higher accuracy tier than its weakest material input.

In a Top 1 proposal:
- Shared journey: `ROAD_ROUTE` (Turn-by-turn road route)
- Solo baseline A: `MATRIX_SCREENING` (Matrix table distance)
- Solo baseline B: `MATRIX_SCREENING` (Matrix table distance)

Because $F_A$ and $F_B$ are material inputs to the allocation weights $W_A, W_B$, the weakest material input is `MATRIX_SCREENING`.
Therefore, under the conservative rule:
$$\text{composite\_accuracy} = \text{MATRIX\_SCREENING}$$

The phrase "Tier 1 Hybrid" is formally eliminated. The system maintains strictly the approved four tiers:
1. `ROAD_ROUTE`
2. `MATRIX_SCREENING`
3. `CALIBRATED_FALLBACK`
4. `GEODESIC_ONLY`

### 5.2 Naming Consistency with Phase 5A Codebase
Source inspection of `backend/app/routing/models.py` established the exact existing StrEnum members and values:

```
+---------------------------------------------------------------------------------------------------------+
|                                  PHASE 5A DISTANCE SOURCE MAPPING                                       |
+------------------------------------------+----------------------------------+---------------------------+
| Phase 5A StrEnum Member                  | String Value                     | Corresponding Fare Tier   |
+------------------------------------------+----------------------------------+---------------------------+
| DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE| "provider_road_network_route"    | ROAD_ROUTE                |
| DistanceSource.PROVIDER_MATRIX_TABLE     | "provider_matrix_table"          | MATRIX_SCREENING          |
| DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK | "calibrated_tortuosity_fallback" | CALIBRATED_FALLBACK       |
| DistanceSource.GEODESIC_SPHEROID         | "geodesic_spheroid"              | GEODESIC_ONLY             |
+------------------------------------------+----------------------------------+---------------------------+
```

The nonexistent identifier `PROVIDER_ROUTE_TURN_BY_TURN` has been completely purged from all documentation and replaced with `DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE` (`"provider_road_network_route"`).

### 5.3 Component-Level Provenance Contract
The API exposes both component-level provenances and the conservative composite accuracy:
```json
{
  "composite_accuracy": "MATRIX_SCREENING",
  "composite_accuracy_explanation": "Conservative rating based on weakest material input. Pooled vehicle route uses turn-by-turn road geometry, while solo baselines are calibrated from matrix table screening.",
  "shared_journey_source": "provider_road_network_route",
  "shared_journey_accuracy": "ROAD_ROUTE",
  "solo_baseline_a_source": "provider_matrix_table",
  "solo_baseline_a_accuracy": "MATRIX_SCREENING",
  "solo_baseline_b_source": "provider_matrix_table",
  "solo_baseline_b_accuracy": "MATRIX_SCREENING"
}
```

---

## 6. Finding F-04 — Waiting Charges and Excluded Costs

### 6.1 Regulatory Waiting-Charge Analysis
- **Authoritative Source:** Khatua Committee Report, Clause 4.18.1 (approved by Government of Maharashtra / MMRTA).
- **Rule:** Waiting/detention charges are calculated on a per-minute basis, pegged at approximately 10% of the per-kilometer rate per minute (₹1.50 to ₹2.20 per minute depending on vehicle category).
- **Metrological Trigger:** Electronic taximeters switch automatically from distance-based pulses to time-based pulses whenever vehicle speed drops below 10 km/h or when stationary.

### 6.2 Pre-Trip Exclusion & API Contract
In a pairwise matching system, traffic signal delays, junction congestion, and passenger boarding delays cannot be deterministically forecast prior to departure.

Therefore:
1. Waiting charges are **strictly excluded** from pre-trip matching fare estimates.
2. Bridge/highway tolls (e.g. Bandra-Worli Sea Link, Coastal Road) and airport pickup fees are **strictly excluded**.
3. All excluded items are explicitly itemized in the API response under `excluded_charges`:
   - `WAITING_TIME`: "Traffic or boarding delay; metered dynamically by taxi meter if incurred."
   - `ROAD_TOLL`: "Sea Link / Coastal Road toll; payable directly at booth or split equally."
   - `PARKING_LEVY`: "Airport pickup levy; payable directly if incurred."
4. User-facing disclaimer states: *"Estimated pre-trip fare based on the configured Mumbai tariff model. This continuous estimate does not reproduce the physical taxi meter's pulse behavior. The final charge is determined by the taxi meter at trip completion. Tolls, waiting time and parking are not included."* Smart Share does not collect payments or guarantee the final meter charge.

---

## 7. Finding F-05 — Correct Savings Divergence Units & Proof

### 7.1 Percentage Points (pp) Clarification
The divergence between Passenger A and Passenger B percentage savings:
$$\Delta_{\text{pp}} = |\text{SavingsPct}_A - \text{SavingsPct}_B|$$
is expressed in **percentage points (pp)**, not as a relative percentage of a percentage.

### 7.2 Strict Derivation and Conditional Assumptions
Let:
- $\text{SavingsPct}_A = \left( 1 - \frac{S_A}{F_A} \right) \times 100$
- $\text{SavingsPct}_B = \left( 1 - \frac{S_B}{F_B} \right) \times 100$
- $S_A = q_A + \epsilon_A$, $S_B = q_B - \epsilon_A$, where $|\epsilon_A| \le \text{₹}0.005$ (half-paisa rounding).

$$\Delta_{\text{pp}} = |\epsilon_A| \left( \frac{1}{F_A} + \frac{1}{F_B} \right) \times 100\text{ percentage points}$$

**Conditional Assumptions:**
1. **Minimum Solo Fare:** $F_A \ge \text{₹}33.00$ and $F_B \ge \text{₹}33.00$ (statutory Mumbai flag drop).
2. **Paise Quantization:** Allocation is rounded to the nearest integer paisa ($0.01\text{ INR}$).
3. **Exact Budget Conservation:** $S_B = F_{\text{shared}} - S_A$.
4. **Proportional Quotas:** $q_A = F_{\text{shared}} \times \frac{F_A}{F_A + F_B}$.

Under these assumptions:
$$\Delta_{\text{pp, max}} \le 0.005 \times \left( \frac{1}{33.00} + \frac{1}{33.00} \right) \times 100 = \frac{1}{330} \times 100 \approx 0.030303\text{ percentage points}$$

**Conclusion:** The test assertion tolerance of **$0.04\text{ percentage points}$** is mathematically proven under the assumption that both solo baselines meet or exceed the statutory minimum fare of ₹33.00.

---

## 8. Finding F-06 — Night Surcharge Boundaries & Timezone

### 8.1 Unambiguous Half-Open Interval
- **Timezone:** `Asia/Kolkata` (UTC+05:30). India does not observe Daylight Saving Time (DST); offset is permanently fixed.
- **Statutory Window:** Half-open interval:
  $$T_{\text{night}} = [00:00:00, \; 05:00:00) \quad \text{IST}$$
  (i.e. $t \ge 00:00:00$ AND $t < 05:00:00$).

### 8.2 Second-by-Second Boundary Behavior

| Timestamp (IST) | Interval Condition | Multiplier Applied | Surcharge Status | Description |
| :--- | :--- | :--- | :--- | :--- |
| `23:59:59` | $t < 00:00:00$ | **1.00** | `NONE` | Last second of daytime tariff |
| `00:00:00` | $00:00:00 \le t < 05:00:00$ | **1.25** | `APPLIED` | First second of statutory night tariff |
| `04:59:59` | $00:00:00 \le t < 05:00:00$ | **1.25** | `APPLIED` | Last second of statutory night tariff |
| `05:00:00` | $t \ge 05:00:00$ | **1.00** | `NONE` | Exact 5:00 AM return to daytime tariff |
| `05:00:01` | $t \ge 05:00:00$ | **1.00** | `NONE` | First second of daytime tariff |

### 8.3 Application to Journey Components & Overlapping Windows
- **Shared Journey ($F_{\text{shared}}$):** Evaluated at the shared departure window midpoint ($t_{\text{mid}}$) in `Asia/Kolkata`.
- **Solo Baseline A ($F_A$):** Evaluated at Passenger A's departure window midpoint in `Asia/Kolkata`.
- **Solo Baseline B ($F_B$):** Evaluated at Passenger B's departure window midpoint in `Asia/Kolkata`.
- **Overlapping Departure Windows:** If $[t_{\text{start}}, t_{\text{end}}]$ spans across midnight or 05:00 IST:
  - `surcharge_status = "CONDITIONAL"`
  - Response includes `fare_range: {"min_possible_fare": DayFare, "max_possible_fare": NightFare}`.

---

## 9. Finding F-07 — Reconfirm Phase 5A Source Contracts

### 9.1 Actual Source Field Names & Types

```
+---------------------------------------------------------------------------------------------------------+
|                                    CONFIRMED PHASE 5A SOURCE CONTRACTS                                  |
+--------------------------+------------------------------+--------------------+--------------------------+
| Context / Location       | Field Name                   | Python Type        | Actual Status in Code    |
+--------------------------+------------------------------+--------------------+--------------------------+
| routing/models.py        | DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE | StrEnum member | Value: "provider_road_network_route" |
| routing/models.py        | DistanceSource.PROVIDER_MATRIX_TABLE       | StrEnum member | Value: "provider_matrix_table"       |
| schemas/matching.py      | total_shared_distance_meters | float              | Exists on MatchProposalSchema |
| schemas/matching.py      | total_shared_distance_km     | float              | Exists on MatchProposalSchema |
| schemas/matching.py      | is_route_approximate         | bool               | Exists on MatchProposalSchema |
| schemas/matching.py      | distance_is_approximate      | bool               | Exists on MatchProposalSchema |
| schemas/matching.py      | distance_source              | str                | Exists on MatchProposalSchema |
| schemas/matching.py      | routing_accuracy             | str                | Exists on MatchProposalSchema |
| schemas/matching.py      | route_legs                   | list[RouteLegSchema]| Exists on MatchProposalSchema|
| matching/service.py      | proposal.direct_a_dist_m     | float              | Exists on MatchProposal dataclass |
| matching/service.py      | proposal.direct_b_dist_m     | float              | Exists on MatchProposal dataclass |
| endpoints/matching.py    | _get_active_owned_request()  | async function     | Enforces JWT caller ownership |
+--------------------------+------------------------------+--------------------+--------------------------+
```

---

## 10. Regulatory References & Citations

1. **Maharashtra Motor Vehicles Rules, 1989 (as amended):**
   - Rules 115A, 118: Fitment, inspection, and operation of taximeters.
   - Authority: Transport Department, Government of Maharashtra.
2. **Legal Metrology (General) Rules, 2011:**
   - Eighth Schedule, Part VIII: Technical specifications, tolerances, and calibration of Taximeters.
   - Issuing Authority: Ministry of Consumer Affairs, Food and Public Distribution, Government of India.
   - Document Ref: GSR 71(E), effective 1 March 2011.
3. **Khatua Committee Report (2017):**
   - Report of the Committee for Fixation of Fare Structure for Auto Rickshaws and Taxis in Maharashtra (Chaired by B.C. Khatua, IAS Retd.).
   - Clause 4.18.1: Detention / waiting charges calculation methodology.
   - Authority: Mumbai Metropolitan Region Transport Authority (MMRTA).
4. **MMRTA Taxi Fare Revision Order (effective 1 September 2026):**
   - Base fare ₹33.00 for initial 1.5 km; ₹21.90/km thereafter; 25% night surcharge (00:00–05:00 IST).

---

## 11. Final Safety & Regression Confirmation

1. **Application Source Code Untouched:** `git status` verifies no files under `backend/app/` or `frontend/src/` have been altered.
2. **Database Schema Untouched:** Database remains at Alembic revision `5b69062ab3ef`.
3. **Environment Secure:** No secrets or credentials were touched, modified, or logged.
4. **Phase 5A Unchanged:** Commit hash `9ebed5d7da24e7ff64bf8912c11e719d4903de90` preserved.
5. **Phase 5B Status:** Implementation has **not** been started. Authorization remains with the Product Owner.
