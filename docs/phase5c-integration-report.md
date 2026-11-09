# Phase 5C Fare Allocation — Integration Report

**Status:** Integrated Locally (Hosted Acceptance Pending)  
**Date:** November 9, 2026  

---

## 1. System Integration Overview

Phase 5C seamlessly integrates into the transient pairwise matching and fare estimation pipeline:
1. **Candidate Discovery & Routing Normalization (Phase 4B / 5A):** Produces turn-by-turn road route metrics for shared pooled journey and direct solo legs.
2. **Statutory Fare Estimation (Phase 5B):** Calculates Mumbai taxi tariff pre-trip estimates for $P_1 \to D_2$ (`shared_journey`), $P_A \to D_A$ (`your_solo_baseline`), and $P_B \to D_B$ (`candidate_solo_baseline`).
3. **Solo-Fare Proportional Cost Allocation (Phase 5C):** Evaluates `calculate_fare_allocation()` using Decimal and integer paise. Generates deterministic contributions and individual savings.
4. **Viewer Privacy Scoping (DEC-013):** Maps domain allocation to `MatchFareEstimateSchema`. Redacts co-passenger solo baselines and contributions unless affirmative bilateral consent is recorded.
5. **UI Fare Presentation (Frontend):** Displays the tripartite breakdown: Original shared trip fare, Solo baseline estimate, and Allocated share with savings or attractiveness indicators.

---

## 2. API Contract Sample (`MatchFareEstimateSchema`)

```json
{
  "shared_journey": {
    "estimate": 197.25,
    "estimate_paise": 19725,
    "rounded_estimate_rupees": 197,
    "distance_meters": 9000.0,
    "distance_source": "provider_road_network_route",
    "accuracy_tier": "ROAD_ROUTE",
    "surcharge_status": "CONDITIONAL",
    "fare_range": {
      "minimum": { "estimate": 197.25, "estimate_paise": 19725, "rounded_estimate_rupees": 197 },
      "maximum": { "estimate": 246.56, "estimate_paise": 24656, "rounded_estimate_rupees": 247 }
    }
  },
  "your_solo_baseline": {
    "estimate": 120.25,
    "estimate_paise": 12025,
    "rounded_estimate_rupees": 120,
    "distance_meters": 5500.0,
    "distance_source": "provider_road_network_route",
    "accuracy_tier": "ROAD_ROUTE",
    "surcharge_status": "CONDITIONAL",
    "fare_range": {
      "minimum": { "estimate": 120.25, "estimate_paise": 12025, "rounded_estimate_rupees": 120 },
      "maximum": { "estimate": 150.31, "estimate_paise": 15031, "rounded_estimate_rupees": 150 }
    }
  },
  "your_allocated_fare": {
    "estimate": 105.25,
    "estimate_paise": 10525,
    "rounded_estimate_rupees": 105
  },
  "your_savings": {
    "estimate": 15.00,
    "estimate_paise": 1500,
    "rounded_estimate_rupees": 15
  },
  "your_savings_percent": 12.47,
  "economic_status": "SAVINGS",
  "is_economically_beneficial": true,
  "co_passenger_contribution": null,
  "composite_accuracy": "MATRIX_SCREENING",
  "fare_model_id": "mumbai_taxi_standard",
  "fare_model_version": "1.0.0",
  "pulse_quantization_mode": "CONTINUOUS",
  "excluded_charges": ["tolls", "waiting time", "parking"],
  "disclaimer": "Estimated pre-trip fare based on the configured Mumbai tariff model. The selected continuous calculation is an estimate and does not claim to reproduce the physical taxi meter's legally unresolved pulse behavior. The final charge is determined by the taxi meter at trip completion. Tolls, waiting time and parking are not included."
}
```

---

## 3. Hosted Two-User Acceptance Checklist (Pending Live Gate)

- [x] Local mathematical allocation verification (181 backend tests passed).
- [x] Local frontend component verification (32 vitest tests passed).
- [x] DEC-013 privacy scoping and unilateral redaction verified in local mocks.
- [ ] Deploy backend revision to hosted FastAPI service.
- [ ] Deploy frontend bundle to Vercel production hosting.
- [ ] Run bilateral consent flow between two distinct authenticated Supabase test accounts.
- [ ] Confirm mutual consent reveals `co_passenger_contribution` on both devices while continuing to redact solo baselines.
