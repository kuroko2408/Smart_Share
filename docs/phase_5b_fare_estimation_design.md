# Smart Share — Phase 5B Technical Design Specification
## Fare Estimation Models (with Phase 5C Allocation Interface)

**Project:** Smart Share — Intelligent Cab-Pooling Platform  
**Target Geography:** Mumbai, India  
**Phase:** Phase 5B — Fare Estimation Models  
**Status:** Phase 5B design aligned to approved DEC-004 estimate policy; DEC-013 remains pending for Phase 5C disclosure.
**Date:** November 8, 2026  
**Related Documents:**
- `docs/phase_5b_fare_model_decisions.md`
- `docs/phase_5b_fare_estimation_test_strategy.md`
- `docs/phase_5b_fare_estimation_risk_analysis.md`
- `docs/phase_5b_final_pre_implementation_audit.md`
- `docs/phase_5b_product_owner_decision_sheet.md`
- `docs/05-roadmap.md`

---

## 1. Executive Summary & Mission

Smart Share enables commuters traveling along compatible corridors in Mumbai to share a black-and-yellow taxi, reducing individual travel expenses, passenger detours, and road congestion.

Phase 5A delivered normalized road network routing, multi-stop pooled route sequencing, and GeoJSON route geometry. Phase 5B implements tariff-based **pre-trip fare estimation** over those route metrics. The related Phase 5C milestone consumes the resulting shared and solo estimates to allocate contributions and calculate savings. The allocation formulas and API fields in Sections 9, 10 and 12 are retained as Phase 5C design inputs; they are not Phase 5B implementation outputs.

Phase 5B responsibilities are tariff model/version selection, shared-journey and solo-baseline fare estimates, surcharge handling, accuracy provenance, and clear estimate-versus-final-charge communication. Its public response must not expose a co-passenger contribution, co-passenger solo baseline, private savings, or private solo route details. Phase 5C disclosure remains blocked pending DEC-013 approval.

---

## 2. Non-Negotiable Architectural Principles

### Principle A: Decoupling from Matching Feasibility
Fare estimation is strictly an evaluative layer that executes **after** pairwise match feasibility has been established. The fare engine never alters candidate discovery, detour screening, or route sequencing. If a fare cannot be estimated, it returns `null` or raises a structured exception without invalidating the match proposal.

### Principle B: Preservation of Phase 5A Route Metrics
The fare engine consumes normalized route metrics produced by Phase 5A (`total_shared_distance_m`, `direct_a_dist_m`, `direct_b_dist_m`, `distance_source`, `is_route_approximate`). It never modifies these route metrics.

### Principle C: Configurable Parameterization
All regulatory rates (base fare, per-km rate, pulse intervals, night multipliers, surcharges) are parameterized in an in-memory `FareModelRegistry`. Business logic contains zero hardcoded tariff rates.

### Principle D: Explicit Provenance and Conservative Aggregation
Every quote explicitly communicates its component-level provenances (`shared_journey_source`, `solo_baseline_a_source`, `solo_baseline_b_source`). In accordance with the weakest-link principle, the aggregate `composite_accuracy` must never claim a higher tier than its weakest material input.

### Principle E: Monetary Precision and Dual Wire Serialization
All internal calculations are conducted strictly in Python `Decimal`. Wire representations provide integer paise alongside float display numbers to prevent IEEE 754 floating-point drift in client browsers.

### Principle F: Estimate Is Not the Final Meter Charge
Every customer-facing amount produced before travel is a **pre-trip fare estimate**. Continuous linear integration is the approved calculation default, not a claim about physical electronic meter pulse behavior. The estimate must not be described as an exact meter reproduction or final charge. The final fare is determined by the physical meter at trip completion, and may differ due to actual distance, meter quantization, traffic/waiting time, tolls, parking and other applicable charges.

---

## 3. Existing Architecture & Integration Boundaries

### 3.1 Actual Phase 5A Data Contract Verification
Source code inspection of `backend/app/routing/models.py`, `backend/app/schemas/matching.py`, and `backend/app/matching/service.py` confirmed:
- `direct_a_dist_m: float`: Passenger A solo direct road distance in meters (domain dataclass).
- `direct_b_dist_m: float`: Passenger B solo direct road distance in meters (domain dataclass).
- `total_shared_distance_m: float`: Total vehicle journey distance ($P_1 \to D_2$) in meters.
- `total_shared_distance_meters: float`: Matching field serialized on `MatchProposalSchema`.
- `total_shared_duration_seconds: float`: Total vehicle journey duration in seconds.
- `distance_source: str`: StrEnum value from `DistanceSource` enum (`DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE`, `DistanceSource.PROVIDER_MATRIX_TABLE`, etc.).
- `is_route_approximate: bool`: True if fallback approximation was used; False if road network route.
- `routing_accuracy: str`: Human-readable provenance descriptor.

### 3.2 Controlled Conversion Boundary
Because Phase 5A models store distances as `float`, the fare engine establishes a strict entry boundary:
```python
d_meters = Decimal(str(proposal.total_shared_distance_m))
d_solo_a = Decimal(str(proposal.direct_a_dist_m))
d_solo_b = Decimal(str(proposal.direct_b_dist_m))
```
Direct conversion `Decimal(val_float)` is prohibited to avoid IEEE 754 binary representation artifacts.

---

## 4. Mumbai Fare Model & Tariff Architecture

### 4.1 Regulatory Framework & Unresolved Metrological Rules
The fare engine models non-AC petrol/CNG black-and-yellow taxis regulated by the Mumbai Metropolitan Region Transport Authority (MMRTA) under the Khatua Committee pricing framework:
- **Flag Drop (Base Fare):** ₹33.00 for the first 1.50 km (1,500 meters).
- **Per-Kilometer Distance Rate:** ₹21.90 per km for distance exceeding 1,500 meters.
- **Pulse Interval:** 100 meters (0.10 km) clocked at ₹2.19 per pulse.
- **Night Surcharge:** 25% extra between 00:00:00 and 04:59:59.999 IST ($[00:00:00, 05:00:00)\text{ IST}$).
- **Statutory Rounding:** Final payable meter fare rounded to nearest integer Rupee ($\le 49\text{ paise} \to \text{down}$, $\ge 50\text{ paise} \to \text{up}$, using `ROUND_HALF_UP`).

**Unresolved Metrological Behavior (Finding F-01):**
Authoritative legal metrology documentation does not definitively establish whether physical electronic meters increment immediately upon entering a new 100m segment (Ceiling $\lceil \cdot \rceil$), only upon completing the 100m segment (Floor $\lfloor \cdot \rfloor$), or use continuous linear rates on printed tariff cards.

### 4.2 Mandatory Boundary Evaluation Across Hypotheses

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

### 4.3 Parameterized Quantization Strategy
The fare engine selects pulse quantization using the runtime setting `FARE_PULSE_QUANTIZATION_MODE` (`CONTINUOUS`, `CEILING`, or `FLOOR`). It defaults to `CONTINUOUS`; tariff rates remain parameterized in the immutable `FareModelConfig` registry:
```python
class PulseQuantizationMode(enum.StrEnum):
    CONTINUOUS = "CONTINUOUS"
    CEILING = "CEILING"
    FLOOR = "FLOOR"
```
- **Approved pre-trip default:** `"CONTINUOUS"` for fare estimates. Any later cost-allocation use is a separate Phase 5C responsibility; this fare-estimation response does not expose allocation values.

This is now the approved Product Owner default for pre-trip fare estimation under DEC-004. CEILING and FLOOR remain configurable hypotheses only. The physical meter's actual pulse quantization is legally unresolved. Do not call the continuous result an exact meter fare. Show a label such as **Estimated pre-trip fare** and state that it is distinct from the final physical meter charge.

---

## 5. Phase 5C Allocation Input — Savings and False Sub-Additivity

Sub-additivity ($F_{\text{shared}} < F_{\text{solo}, A} + F_{\text{solo}, B}$) is not assumed as a mathematical axiom. In circuitous detours, a pooled journey can exceed the sum of solo direct routes ($F_{\text{shared}} > F_{\text{solo}, A} + F_{\text{solo}, B}$), resulting in dissavings (negative savings).

The fare engine classifies savings into three operational statuses:
1. `POSITIVE` ($F_{\text{shared}} < F_{\text{solo}, A} + F_{\text{solo}, B}$): Cab pooling reduces costs for both passengers.
2. `BREAK_EVEN` ($F_{\text{shared}} == F_{\text{solo}, A} + F_{\text{solo}, B}$): Exact neutrality.
3. `NEGATIVE` ($F_{\text{shared}} > F_{\text{solo}, A} + F_{\text{solo}, B}$): Circuitous detour. Flagged with positive `detour_surcharge` and negative savings.

---

## 6. Timezone & Night-Surcharge Policy

### 6.1 Unambiguous Half-Open Interval
- **Timezone:** `Asia/Kolkata` (UTC+05:30). India does not observe Daylight Saving Time (DST).
- **Statutory Window:** Half-open interval:
  $$T_{\text{night}} = [00:00:00, \; 05:00:00) \quad \text{IST}$$
  (i.e. $t \ge 00:00:00$ AND $t < 05:00:00$).

### 6.2 Second-by-Second Boundary Behavior
- `23:59:59 IST`: Multiplier **1.00** (`surcharge_status = "NONE"`)
- `00:00:00 IST`: Multiplier **1.25** (`surcharge_status = "APPLIED"`)
- `04:59:59 IST`: Multiplier **1.25** (`surcharge_status = "APPLIED"`)
- `05:00:00 IST`: Multiplier **1.00** (`surcharge_status = "NONE"`)
- `05:00:01 IST`: Multiplier **1.00** (`surcharge_status = "NONE"`)

### 6.3 Application to Components & Overlapping Windows
- **Shared Journey ($F_{\text{shared}}$):** Evaluated at the shared departure window midpoint ($t_{\text{mid}}$) in `Asia/Kolkata`.
- **Solo Baselines ($F_A, F_B$):** Evaluated at each passenger's departure window midpoint in `Asia/Kolkata`.
- **Overlapping Windows:** If $[t_{\text{start}}, t_{\text{end}}]$ spans across midnight or 05:00 IST:
  - `surcharge_status = "CONDITIONAL"`
  - Exposes `fare_range: {"min_possible_fare": DayFare, "max_possible_fare": NightFare}`.

---

## 7. Route Accuracy Tiers & Conservative Aggregation

### 7.1 Accuracy Hierarchy
The system strictly maintains four accuracy tiers:
- **Tier 1: `ROAD_ROUTE`**: Turn-by-turn road geometry from provider (`DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE`).
- **Tier 2: `MATRIX_SCREENING`**: Distance-matrix table lookups (`DistanceSource.PROVIDER_MATRIX_TABLE`).
- **Tier 3: `CALIBRATED_FALLBACK`**: Haversine distance scaled by Mumbai urban circuity factor (`DistanceSource.CALIBRATED_TORTUOSITY_FALLBACK`).
- **Tier 4: `GEODESIC_ONLY`**: Raw straight-line Haversine (`DistanceSource.GEODESIC_SPHEROID`).

### 7.2 The Weakest-Link Conservative Aggregation Rule
In Top 1 proposals:
- Shared journey: `DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE` (`ROAD_ROUTE`).
- Solo baselines: `DistanceSource.PROVIDER_MATRIX_TABLE` (`MATRIX_SCREENING`).

Under the weakest-link rule, an aggregate estimate cannot claim a higher tier than its weakest material input:
$$\text{composite\_accuracy} = \text{MATRIX\_SCREENING}$$

The phrase "Tier 1 Hybrid" is formally eliminated. The API exposes both component provenances and the conservative composite accuracy.

### 7.3 Mandatory On-Demand Route Enrichment Recalculation
When a user requests proposal detail for proposals 2..N via `get_proposal_detail()`, Phase 5A triggers on-demand road-route enrichment. The fare engine is immediately re-invoked with the enriched road distance, updating `shared_journey_source` to `DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE`.

---

## 8. Monetary Precision & Rounding Policy

### 8.1 Precision Specifications
- All calculations conducted in `Decimal`.
- Intermediate weights maintain at least 8 decimal places.
- Wire amounts serialized as integer paise alongside rounded float numbers.

### 8.2 Exact Budget Balance Invariant
$$S_A + S_B = F_{\text{shared}} \quad (\text{exact down to } 0.0000)$$

### 8.3 Mathematical Derivation of Percentage Savings Tolerance
Let:
- $\text{SavingsPct}_A = \left( 1 - \frac{S_A}{F_A} \right) \times 100\text{ percentage points}$
- $\text{SavingsPct}_B = \left( 1 - \frac{S_B}{F_B} \right) \times 100\text{ percentage points}$
- $|\epsilon_A| \le \text{₹}0.005$ (half-paisa rounding).

$$\Delta_{\text{pp}} = |\epsilon_A| \left( \frac{1}{F_A} + \frac{1}{F_B} \right) \times 100\text{ percentage points}$$

**Conditional Assumptions:**
1. Both solo baselines satisfy statutory minimum fare: $F_A \ge \text{₹}33.00, F_B \ge \text{₹}33.00$.
2. Paise quantization ($0.01\text{ INR}$).
3. Exact budget conservation ($S_B = F_{\text{shared}} - S_A$).
4. Proportional allocation method.

Under these assumptions:
$$\Delta_{\text{pp, max}} \le 0.005 \times \left( \frac{1}{33.00} + \frac{1}{33.00} \right) \times 100 = \frac{1}{330} \times 100 \approx 0.030303\text{ percentage points}$$
The test assertion tolerance is fixed at **$0.04\text{ percentage points}$**.

---

## 9. Phase 5C — Cost Allocation Mathematics & Worked Examples

This section is the allocation contract for Phase 5C, downstream of the Phase 5B estimate engine. It does not authorize Phase 5B to expose the co-passenger's contribution.

### 9.1 Formulation & Hamilton-Hare Equivalence Proof
Quotas:
$$q_A = F_{\text{shared}} \times \frac{F_A}{F_A + F_B}, \qquad q_B = F_{\text{shared}} \times \frac{F_B}{F_A + F_B}$$

Allocation:
$$S_A = q_A.\text{quantize}(\text{Decimal}("0.01"), \; \text{ROUND\_HALF\_UP})$$
$$S_B = F_{\text{shared}} - S_A$$

**Equivalence Proof:** Because $q_A + q_B = N \in \mathbb{Z}$ (integer paise), fractional remainders satisfy $r_B = 1 - r_A$.
Therefore, $r_A > r_B \iff r_A > 0.5$.
Largest-Remainder (Hamilton-Hare) allocation with tie-breaking to Passenger A produces identical results to `ROUND_HALF_UP` on $S_A$ and remainder to $S_B$ across all possible inputs (verified empirically across 10,000 cases with 0 mismatches).

### 9.2 Monotonicity Under Ceteris Paribus
For fixed co-passenger solo fare $F_B$ and fixed shared fare $F_{\text{shared}}$:
$$\frac{\partial q_A}{\partial F_A} = F_{\text{shared}} \frac{F_B}{(F_A + F_B)^2} > 0$$
Allocated share $S_A$ is strictly non-decreasing with respect to $F_A$ when $F_B$ and $F_{\text{shared}}$ are held constant.

---

## 10. Phase 5C — Passenger-Specific API Visibility & Privacy (DEC-013)

### 10.1 Direct vs Inferential Disclosure
- **Direct Redaction:** The API never exposes `co_passenger_solo_fare`, `co_passenger_savings`, or `co_passenger_direct_distance`.
- **Inferential Disclosure:** Because proportional allocation provides `your_fare` ($S_A$), `co_passenger_contribution` ($S_B$), and `total_shared_fare` ($F_{\text{shared}}$), a user can infer:
  $$F_B^* = F_A \times \frac{S_B}{S_A}$$
  Accurate to within $\pm 2\text{ paise}$.

### 10.2 Product Owner Decision (DEC-013)
The exact-contribution policy is **PROPOSED and PENDING FINAL PRODUCT OWNER APPROVAL**. If approved, implement bilateral, explicit opt-in before either participant sees an exact split. The notice must state that exact contributions enable approximate inference of the other participant's solo baseline and, with shared endpoints or external information, may support distance inference; consent acknowledges this residual risk rather than removing it. Do not rely on general terms or silence. Record each participant's consent version, time and selected disclosure mode through an approved auditable mechanism. A decline or pre-confirmation withdrawal prevents exact contribution disclosure.

Keep the other participant's direct solo baseline fare, savings, direct distance and private solo route geometry/waypoints redacted. Shared pickup/dropoff and pooled itinerary details required to decide whether to share are purpose-limited shared-trip data, not permission to reveal solo-route data.

If exact disclosure is rejected, use the proposed nearest-₹10 bucketed contribution policy only after reviewing the whole response for algebraic reconstruction. Exact `total_shared_fare` plus exact `your_allocated_fare` reveals the co-passenger contribution even if the contribution field is hidden; the alternative must coarsen or withhold linked values as needed. Bucketing reduces precision and must not be represented as eliminating inference.

---

## 11. Structured Included & Excluded Charges

### Included in Pre-Trip Estimate:
1. `FLAG_DROP`: ₹33.00 for the first 1.5 km.
2. `DISTANCE_FARE`: ₹21.90/km distance progression.
3. `NIGHT_SURCHARGE`: 25% extra between 00:00 and 05:00 IST (when applicable).

### Excluded from Pre-Trip Estimate:
1. `TOLL`: Bandra-Worli Sea Link, Coastal Road tolls (split equally or settled directly).
2. `WAITING_TIME`: Traffic or boarding delays (Khatua Committee Clause 4.18.1; metered dynamically if incurred).
3. `AIRPORT_PARKING`: Airport pickup/parking levies.

**Required estimate disclaimer:** *"Estimated pre-trip fare based on the configured Mumbai tariff model; this continuous estimate does not reproduce the physical taxi meter's pulse behavior. The final charge is determined by the taxi meter at trip completion. Tolls, waiting time and parking are not included."* Smart Share does not collect payments or guarantee the final meter charge.

---

## 12. Proposed Phase 5C API Schema Design

This is a downstream allocation response target, not the Phase 5B fare-estimation response. Phase 5B may calculate both solo baselines internally for use by Phase 5C, but it must not expose the co-passenger contribution, solo baseline, savings, or private solo-route details.

```python
class IncludedChargeSchema(BaseModel):
    charge_type: str
    description: str
    amount: float
    amount_paise: int

class ExcludedChargeSchema(BaseModel):
    charge_type: str
    description: str
    policy: str

class ConditionalFareRangeSchema(BaseModel):
    min_possible_fare: float
    min_possible_fare_paise: int
    max_possible_fare: float
    max_possible_fare_paise: int

class MatchProposalFareSchema(BaseModel):
    total_shared_fare: float
    total_shared_fare_paise: int
    your_allocated_fare: float
    your_allocated_fare_paise: int
    your_solo_baseline_fare: float
    your_solo_baseline_fare_paise: int
    your_savings: float
    your_savings_paise: int
    your_savings_percent: float
    # Phase 5C only; disclose exact values only after DEC-013 consent.
    co_passenger_contribution: float
    co_passenger_contribution_paise: int

    pricing_model_id: str = "mumbai_taxi_standard"
    pricing_model_version: str = "1.0.0"
    composite_accuracy: str = "MATRIX_SCREENING"
    composite_accuracy_explanation: str
    shared_journey_source: str
    shared_journey_accuracy: str
    solo_baseline_a_source: str
    solo_baseline_a_accuracy: str
    solo_baseline_b_source: str
    solo_baseline_b_accuracy: str

    surcharge_status: str
    fare_range: ConditionalFareRangeSchema | None = None

    included_charges: list[IncludedChargeSchema]
    excluded_charges: list[ExcludedChargeSchema]

    disclaimer: str
    calculated_at: datetime
```

---

## 13. Verification & Safety Confirmation

Phase 5B implementation was authorized after the Product Owner approved continuous linear pre-trip estimation. Physical meter pulse behavior remains legally unresolved. DEC-013 is a Phase 5C disclosure decision and does not block the isolated Phase 5B estimator. No Phase 5C behavior is authorized by this design.

## 14. Phase 5B Implementation Contract

The implementation attaches `fare_estimate` to the existing matching proposal response for discovery and proposal detail. It contains `shared_journey` and the authenticated request owner's `your_solo_baseline`; it never serializes the candidate's solo fare. Existing passenger solo-distance detail is also limited to the viewer's request. The shared itinerary and compatibility detour information remain available.

The estimate uses `FARE_PULSE_QUANTIZATION_MODE` (`CONTINUOUS`, `CEILING`, or `FLOOR`), defaulting to `CONTINUOUS`. Fare math uses Python `Decimal`, serializes paise and a rounded whole-rupee estimate, and evaluates the Asia/Kolkata `[00:00, 05:00)` night interval. Day/night-spanning windows receive a conditional range. Four route sources map to the four approved accuracy tiers; the composite reports the weakest material source.

An unsupported route source or invalid fare input makes `fare_estimate` null without discarding an otherwise feasible match. No schema migration or fare persistence is required. Phase 5B contains no allocation, contribution, savings, consent, or fare-splitting behavior.
