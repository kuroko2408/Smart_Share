# Smart Share — Phase 5B Fare Estimation Risk Analysis & Mitigation Matrix (Post-Audit Targeted Amendment)

**Project:** Smart Share — Intelligent Cab-Pooling Platform  
**Target Geography:** Mumbai, India  
**Phase:** Phase 5B — Fare Estimation Models  
**Status:** Risk Analysis (Pending Product Owner Decision Approvals on DEC-004 & DEC-013)  
**Date:** November 8, 2026  
**Related Documents:**
- `docs/phase_5b_fare_estimation_design.md`
- `docs/phase_5b_fare_model_decisions.md`
- `docs/phase_5b_fare_estimation_test_strategy.md`
- `docs/phase_5b_final_pre_implementation_audit.md`

---

## 1. Executive Summary

Phase 5B introduces financial estimation, regulatory tariff compliance, and cost-sharing models to Smart Share. Incorrect calculations, rounding discrepancies, unverified metrological assumptions, or data privacy leaks directly impair user trust, legal compliance, and platform adoption.

Following the targeted audit on November 8, 2026, this risk analysis evaluates technical, operational, financial, legal, and privacy risks, specifying concrete, audited mitigations for each failure mode.

---

## 2. Comprehensive Risk Matrix

| Risk ID | Risk Domain | Description | Likelihood | Impact | Severity | Post-Mitigation Severity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RISK-TECH-01** | Technical | IEEE 754 binary floating-point drift in client UI | High | Medium | **HIGH** | **LOW** |
| **RISK-TECH-02** | Technical | Stale matrix fares paired with enriched road geometry | High | Medium | **HIGH** | **LOW** |
| **RISK-TECH-03** | Technical | Zero denominator or corrupted metric inputs | Low | High | **MEDIUM** | **LOW** |
| **RISK-TECH-04** | Technical | Timezone desynchronization between UTC and IST | Medium | High | **HIGH** | **LOW** |
| **RISK-FIN-01** | Financial | Paisa leakage violating budget balance invariant | Medium | High | **HIGH** | **ZERO** (Eliminated) |
| **RISK-FIN-02** | Financial | Systematic rounding bias penalizing Passenger B | Medium | Low | **LOW** | **ZERO** (Eliminated) |
| **RISK-FIN-03** | Financial | Negative savings (dissavings) causing user confusion | Medium | Medium | **MEDIUM** | **LOW** |
| **RISK-REG-01** | Regulatory | Pulse quantization ambiguity at fractional 100m boundaries | High | Medium | **HIGH** | **LOW** (Pending PO Mode) |
| **RISK-REG-02** | Regulatory | Surcharge window overlap on midnight/dawn boundaries | Medium | High | **HIGH** | **LOW** |
| **RISK-PRIV-01** | Privacy | Reverse-engineering co-passenger solo trip baseline | High | Low | **MEDIUM** | **LOW** (Pending PO Sign-off) |

---

## 3. Detailed Risk Analysis & Mitigations

### 3.1 Technical Risks

#### RISK-TECH-01: IEEE 754 Binary Floating-Point Drift
- **Threat:** Serializing currency as standard JSON numbers (e.g. `219.15`) causes JavaScript double-precision approximation artifacts in client browsers (`219.14999999999998`), leading to UI display bugs or failed sum checks.
- **Audited Mitigation:**
  1. Backend arithmetic uses Python `Decimal` exclusively.
  2. The API schema implements a **dual wire format**: standard float fields for UI display plus integer `_paise` fields (e.g. `total_shared_fare_paise: 21900`) for exact client-side validation.

#### RISK-TECH-02: Stale Matrix Fares Paired with Enriched Road Geometry
- **Threat:** When a user inspects proposal details for proposals 2..N, Phase 5A on-demand enrichment updates the route geometry to turn-by-turn road distance. If the fare estimate is not recalculated, the UI displays road geometry alongside obsolete matrix-derived fares.
- **Audited Mitigation:**
  1. DEC-011 mandates that `enrich_route_geometry()` triggers immediate fare re-estimation.
  2. Updates `shared_journey_source` to `DistanceSource.PROVIDER_ROAD_NETWORK_ROUTE`.

#### RISK-TECH-03: Zero Denominator or Corrupted Metric Inputs
- **Threat:** If an upstream service or corrupted input provides $d_{\text{solo}, A} = 0$ and $d_{\text{solo}, B} = 0$, proportional allocation would divide by zero.
- **Audited Mitigation:**
  1. Minimum fare is guaranteed by flag drop ($F_{\text{base}} = \text{₹}33.00$).
  2. Allocator includes defensive validation: `if total_solo <= 0: raise InvalidFareInputError()`.

#### RISK-TECH-04: Timezone Desynchronization
- **Threat:** Comparing UTC departure timestamps directly against Indian night surcharge hours (00:00–05:00) without timezone conversion would apply night tariffs during Indian afternoon hours.
- **Audited Mitigation:**
  1. Explicit timezone conversion boundary using `zoneinfo.ZoneInfo("Asia/Kolkata")` prior to evaluating surcharge hour intervals.
  2. Unambiguous half-open interval $[00:00:00, 05:00:00)\text{ IST}$.
  3. Input validator rejects timezone-naive datetimes.

---

### 3.2 Financial & Economic Risks

#### RISK-FIN-01: Paisa Leakage Violating Budget Balance
- **Threat:** Independent rounding of Passenger A and Passenger B shares could produce $S_A + S_B \ne F_{\text{shared}}$, resulting in financial disputes with the driver.
- **Audited Mitigation:**
  1. Sum conservation is enforced by invariant: $S_B = F_{\text{shared}} - S_A$.
  2. Mathematically guaranteed budget balance down to 0.0000.

#### RISK-FIN-02: Systematic Rounding Bias
- **Threat:** Assigning the remainder exclusively to Passenger B could theoretically produce a 1-paisa systematic bias.
- **Audited Mitigation:**
  1. Formal mathematical proof established that for two passengers, proportional allocation with `ROUND_HALF_UP` on $S_A$ is mathematically identical to the **Largest-Remainder (Hamilton-Hare) Method** with deterministic tie-breaking.
  2. Verified across 10,000 randomized test cases with 0 mismatches.

#### RISK-FIN-03: Negative Savings (Dissavings)
- **Threat:** Extreme detour routes can result in a shared fare exceeding the sum of solo fares ($F_{\text{shared}} > F_{\text{solo}, A} + F_{\text{solo}, B}$), confusing users.
- **Audited Mitigation:**
  1. System explicitly detects negative savings (`savings_status = "NEGATIVE"`).
  2. UI displays positive `detour_surcharge` in amber warning styling, explaining that the detour exceeds pooling benefits.

---

### 3.3 Regulatory & Privacy Risks

#### RISK-REG-01: Pulse Quantization Ambiguity
- **Threat:** Legal metrology specifications for Mumbai electronic meters are inconclusive regarding whether 1,501m clocks a pulse immediately (Ceiling) or upon completion (Floor).
- **Audited Mitigation:**
  1. Quantization mode is parameterized in `FareModelConfig` (`CONTINUOUS`, `CEILING`, `FLOOR`).
  2. Default recommendation is `"CONTINUOUS"` for smooth allocation weights.
  3. Final mode selection is submitted for Product Owner approval.

#### RISK-REG-02: Surcharge Overlap on Boundary Windows
- **Threat:** A departure window crossing 00:00 or 05:00 IST could lead to passenger disputes if the ride is billed at night rate while quoted at day rate.
- **Audited Mitigation:**
  1. Overlapping departure windows return `surcharge_status = "CONDITIONAL"`.
  2. API exposes `fare_range: {"min_possible_fare": DayFare, "max_possible_fare": NightFare}`.
  3. UI renders estimated range and explanatory notice.

#### RISK-PRIV-01: Co-Passenger Baseline Reverse-Engineering (DEC-013)
- **Threat:** Proportional allocation allows a passenger to approximate $F_B \approx F_A \times S_B / S_A$ to within $\pm 2\text{ paise}$.
- **Audited Mitigation:**
  1. Direct fields (`co_passenger_solo_fare`, `direct_b_dist_m`, private savings) remain strictly redacted.
  2. Candidate pickup and dropoff points are already visible in `MatchCandidateSummarySchema` to enable trip decisions.
  3. The inferential disclosure is submitted as an explicit Product Owner decision (DEC-013) pending formal sign-off.
