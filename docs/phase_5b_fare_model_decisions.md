# Smart Share — Phase 5B Architectural Decisions Record (ADR)
## Fare Estimation Models, Cost Allocation & Lifecycle Strategy (Post-Audit Targeted Amendment)

**Project:** Smart Share — Intelligent Cab-Pooling Platform  
**Target Geography:** Mumbai, India  
**Phase:** Phase 5B — Fare Estimation Models  
**Status:** Decisions Recorded (Pending Product Owner Decision Approvals on DEC-004 & DEC-013)  
**Date:** November 8, 2026  
**Related Documents:**
- `docs/phase_5b_fare_estimation_design.md`
- `docs/phase_5b_fare_estimation_test_strategy.md`
- `docs/phase_5b_fare_estimation_risk_analysis.md`
- `docs/phase_5b_final_pre_implementation_audit.md`

---

## 1. Overview & Context

This document records the authoritative architectural decisions for Phase 5B (Fare Estimation Models).

Following the targeted audit conducted on November 8, 2026, all decisions have been amended to resolve metrological pulse quantization ambiguities, enforce the conservative weakest-link accuracy aggregation rule, establish exact half-open surcharge intervals, eliminate naming discrepancies with the Phase 5A codebase, and formalize the economic privacy trade-off for Product Owner review.

---

## 2. Decision Records

### DEC-004: Mumbai Fare Pricing Model & Parameterized Pulse Quantization
- **Status:** Partially Approved — Pulse Quantization Strategy Pending PO Selection
- **Context:** Mumbai black-and-yellow taxis operate under statutory MMRTA tariffs. While base rates (₹33.00 for 1.5 km, ₹21.90/km, 25% night surcharge) are established, authoritative evidence is inconclusive regarding whether physical taximeters clock a 100m pulse immediately upon entering (Ceiling $\lceil \cdot \rceil$), only upon completing the 100m segment (Floor $\lfloor \cdot \rfloor$), or use continuous distance rates on printed tariff cards.
- **Decision:**
  1. The pricing model `mumbai_taxi_standard` defines:
     - **Flag Drop (Base Fare):** ₹33.00 for the first 1.50 km (1,500 meters).
     - **Per-Kilometer Distance Rate:** ₹21.90 per km for distance exceeding 1,500 meters.
     - **Pulse Slab:** 100 meters (0.10 km) clocked at ₹2.19 per pulse.
     - **Night Surcharge:** 25% extra between 00:00:00 and 04:59:59.999 IST ($[00:00:00, 05:00:00)\text{ IST}$).
     - **Statutory Rounding:** Half-up to the nearest integer Rupee applied to the final gross fare after surcharge.
  2. **Pulse Quantization Parameterization:** The fare engine parameterizes the pulse quantization strategy via `pulse_quantization_mode: Literal["CONTINUOUS", "CEILING", "FLOOR"]`.
     - *Default Recommendation:* `"CONTINUOUS"` for pre-trip matching allocations to prevent artificial step-discontinuities in cost-sharing weights $W_A, W_B$.
  3. Waiting charges (Khatua Committee Clause 4.18.1) and road tolls are excluded from pre-trip estimates and itemized under `excluded_charges`.
- **Consequences:** Provides exact legal alignment while allowing the Product Owner to select the final meter quantization mode without code rewrites.

---

### DEC-005: Fare Configuration Storage & Registry Pattern
- **Status:** Approved
- **Context:** Storing tariffs in application database tables creates multi-region migration complexity and testing hurdles.
- **Decision:**
  1. Implement an in-memory, thread-safe `FareModelRegistry`.
  2. Fare models are represented as immutable Pydantic models (`FareModelConfig`) containing semantic versions, effective date intervals, currency, vehicle category, and rates.
  3. Selection is deterministic: Given a location (`mumbai`) and ride departure timestamp, the registry resolves the exact model version active at that point in time.
- **Consequences:** Fast in-memory resolution ($O(1)$), 100% unit-testable in isolation, zero database locks or migrations.

---

### DEC-006: Solo Fare Baseline Route Source
- **Status:** Approved
- **Context:** To calculate passenger savings, the platform must determine what each passenger would have paid traveling alone.
- **Decision:**
  1. Solo baseline distances ($d_{\text{solo}, A}, d_{\text{solo}, B}$) are derived directly from Phase 5A direct metrics (`proposal.direct_a_dist_m`, `proposal.direct_b_dist_m`).
  2. Baseline fares are computed using the identical tariff model (`mumbai_taxi_standard`) and departure window as the shared ride.
- **Consequences:** Ensures fair, apples-to-apples economic comparison without incurring additional routing API requests.

---

### DEC-007: Shared Vehicle Fare, Timezone Standard & Overlapping Windows
- **Status:** Approved
- **Context:** Surcharge windows must be unambiguous and handle departure uncertainty deterministically.
- **Decision:**
  1. **Journey Totals:** Total shared fare $F_{\text{shared}}$ is evaluated on the complete vehicle journey ($P_1 \to D_2$) using `total_shared_distance_m` and `total_shared_duration_seconds`.
  2. **Timezone Policy:** All timestamps are ingested and persisted as timezone-aware UTC (`datetime.now(timezone.utc)`). Surcharge evaluation converts UTC to `Asia/Kolkata` (`zoneinfo.ZoneInfo("Asia/Kolkata")`).
  3. **Half-Open Night Interval:** $[00:00:00, \; 05:00:00)\text{ IST}$.
     - `23:59:59` $\to$ Day (1.00)
     - `00:00:00` $\to$ Night (1.25)
     - `04:59:59` $\to$ Night (1.25)
     - `05:00:00` $\to$ Day (1.00)
  4. **Overlapping Departure Windows:** If $[t_{\text{start}}, t_{\text{end}}]$ spans across midnight or 05:00 IST:
     - Primary estimate evaluates at window midpoint.
     - API returns `surcharge_status = "CONDITIONAL"` and `fare_range: {"min_possible_fare": DayFare, "max_possible_fare": NightFare}`.
- **Consequences:** Deterministic, dispute-free quotes for late-night rides.

---

### DEC-008: Cost Allocation Method & Hamilton-Hare Equivalence
- **Status:** Approved
- **Context:** Cost allocation must conserve every paisa, be non-negative, and provide approximately equal percentage savings.
- **Decision:**
  1. **Proportional-to-Solo-Fare Allocation:**
     $$W_A = \frac{F_{\text{solo}, A}}{F_{\text{solo}, A} + F_{\text{solo}, B}}, \qquad W_B = \frac{F_{\text{solo}, B}}{F_{\text{solo}, A} + F_{\text{solo}, B}}$$
     $$S_A = (W_A \times F_{\text{shared}}).\text{quantize}(\text{Decimal}("0.01"), \; \text{ROUND\_HALF\_UP})$$
     $$S_B = F_{\text{shared}} - S_A$$
  2. **Equivalence:** For two passengers dividing integer paise, this formula is mathematically identical to the Largest-Remainder (Hamilton-Hare) Method with deterministic tie-breaking to Passenger A.
  3. **Budget Conservation:** $S_A + S_B \equiv F_{\text{shared}}$ exact down to 0.0000 paise.
  4. **Monotonicity:** Holds strictly under the ceteris paribus condition ($F_B$ and $F_{\text{shared}}$ constant: $\partial S_A / \partial F_A > 0$).
- **Consequences:** Guaranteed sum conservation and provable fairness.

---

### DEC-009: Monetary Precision, Savings Tolerance & Dual Wire Serialization
- **Status:** Approved
- **Context:** Financial calculations must avoid IEEE 754 floating-point drift in client browsers.
- **Decision:**
  1. **Backend Arithmetic:** Conducted strictly in Python `Decimal`.
  2. **Percentage Savings Tolerance:** Formally proven upper bound of percentage savings divergence is:
     $$\Delta_{\text{pp, max}} \le 0.005 \times \left( \frac{1}{33} + \frac{1}{33} \right) \times 100 \approx 0.030303\text{ percentage points}$$
     The test assertion tolerance is fixed at **$0.04\text{ percentage points}$**, conditional on $F_A, F_B \ge \text{₹}33.00$.
  3. **Dual Wire Contract:** The REST API schema provides dual representations:
     - Float fields (`total_shared_fare: 219.00`, `your_allocated_fare: 128.00`) for direct UI component display.
     - Integer paise fields (`total_shared_fare_paise: 21900`, `your_allocated_fare_paise: 12800`) for exact client-side reconciliation.
- **Consequences:** Absolute financial precision and zero IEEE 754 drift.

---

### DEC-010: Route Accuracy Tiers & Conservative Aggregation Rule
- **Status:** Approved
- **Context:** Previous design labeled composite accuracy as "Tier 1 Hybrid", violating the weakest-link principle.
- **Decision:**
  1. The platform maintains strictly four accuracy tiers:
     - `ROAD_ROUTE`
     - `MATRIX_SCREENING`
     - `CALIBRATED_FALLBACK`
     - `GEODESIC_ONLY`
  2. **Conservative Aggregation Rule:** An aggregate estimate must not claim a higher accuracy tier than its weakest material input.
     - In Top 1 enriched proposals: Shared route is `DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE` (`ROAD_ROUTE`), while solo baselines are `DistanceSource.PROVIDER_MATRIX_TABLE` (`MATRIX_SCREENING`).
     - Because solo baselines are material inputs, the composite accuracy is rated conservatively as:
       $$\text{composite\_accuracy} = \text{MATRIX\_SCREENING}$$
  3. The phrase "Tier 1 Hybrid" is formally eliminated.
  4. The API exposes component-level provenances alongside the conservative composite tier.
- **Consequences:** Completely transparent provenance reporting without overstating fare accuracy.

---

### DEC-011: API Integration & Mandatory Enrichment Recalculation
- **Status:** Approved
- **Context:** When a user requests proposal detail for proposals 2..N via `get_proposal_detail()`, Phase 5A triggers on-demand road-route enrichment.
- **Decision:**
  1. Whenever route enrichment updates `proposal.total_shared_distance_m`, the fare engine is immediately re-invoked with the enriched road distance.
  2. Component-level provenances are updated to reflect the turn-by-turn road route for the shared vehicle journey.
- **Consequences:** Ensures users always see updated, highly accurate fares when inspecting proposal details.

---

### DEC-012: Fare Model Versioning & Zero-Migration Lifecycle
- **Status:** Approved
- **Context:** Tariffs change over time under government regulatory notifications.
- **Decision:**
  1. Fare models adopt semantic versioning (`1.0.0`, `1.1.0`).
  2. Configurations in `FareModelRegistry` are immutable once loaded.
  3. Future tariff revisions are deployed via catalog entries without database schema migrations.
- **Consequences:** Auditability, reproducibility of historical quotes, zero migration downtime.

---

### DEC-013: Intentional Disclosure of Co-Passenger Contribution in Proportional Allocation
- **Status:** **PENDING PRODUCT OWNER APPROVAL**
- **Context:** Proportional allocation ($S_A / S_B = F_A / F_B$) mathematically allows any user who knows their own share $S_A$, their own solo baseline $F_A$, and the co-passenger contribution $S_B = F_{\text{shared}} - S_A$ to infer the co-passenger's solo baseline fare:
  $$F_B^* = F_A \times \frac{S_B}{S_A}$$
  Accounting for paise rounding, $F_B$ can be estimated to within $\pm 2\text{ paise}$.
- **Proposed Decision:**
  1. The product intentionally discloses `co_passenger_contribution` ($S_B$) and `total_shared_fare` ($F_{\text{shared}}$) as part of transparent shared-cost billing.
  2. This inferential disclosure is acceptable because:
     - In cab pooling, passengers must verify that their combined payments equal the taxi meter amount ($S_A + S_B = F_{\text{shared}}$).
     - Direct solo baseline fields, private savings, and private non-shared route coordinates remain strictly redacted.
     - Candidate pickup and dropoff points are already visible in `MatchCandidateSummarySchema` to enable trip decisions; knowing trip distance reveals no new location data.
  3. If the Product Owner rejects inferential disclosure, an alternative mitigation must be approved:
     - *Mitigation Option B (Bucketing):* Round displayed contributions to the nearest ₹10.
     - *Mitigation Option C (Independent Fixed Quotes):* Display only the viewer's allocated fare, suppressing $S_B$ and $F_{\text{shared}}$.
- **Consequences:** Requires formal Product Owner sign-off before implementation can be authorized.

---

## 3. Summary of Decisions & Sign-Off Matrix

| Decision ID | Domain | Primary Mechanism | Governance Status |
| :--- | :--- | :--- | :--- |
| **DEC-004** | Mumbai Tariff | Flag drop ₹33, ₹21.90/km, parameterized quantization | **Partially Approved (Pulse Mode Pending PO)** |
| **DEC-005** | Configuration | In-memory immutable `FareModelRegistry` | Approved |
| **DEC-006** | Solo Baselines | Phase 5A direct metrics (`direct_a_dist_m`) | Approved |
| **DEC-007** | Shared & Night Fare | Vehicle journey ($P_1 \to D_2$), $[00:00, 05:00)\text{ IST}$ | Approved |
| **DEC-008** | Cost Allocation | Proportional allocation, Hamilton-Hare equivalence | Approved |
| **DEC-009** | Precision & Wire | Decimal arithmetic, $0.04\text{ pp}$ tolerance, dual paise wire | Approved |
| **DEC-010** | Route Provenance | Conservative aggregation rule (`MATRIX_SCREENING`) | Approved |
| **DEC-011** | Recalculation | Mandatory fare re-estimation on detail enrichment | Approved |
| **DEC-012** | Model Lifecycle | Semantic versioning and effective date intervals | Approved |
| **DEC-013** | Economic Privacy | Intentional disclosure of $S_B$; inferential baseline risk | **PENDING PRODUCT OWNER APPROVAL** |
