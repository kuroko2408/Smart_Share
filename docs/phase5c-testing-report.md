# Phase 5C Fare Allocation — Testing Report

**Status:** Complete  
**Date:** November 9, 2026  
**Test Suite:** Backend Pytest (`backend/app/tests/test_fares.py`, `backend/app/tests/test_matching_phase5a.py`), Frontend Vitest (`frontend/src/features/ride-requests/__tests__/RideRequests.test.tsx`)

---

## 1. Mathematical and Financial Invariants Verification

The Phase 5C allocation engine enforces 12 core mathematical and financial invariants, verified by automated unit tests:

| Invariant # | Description | Test Function | Test Outcome |
| :--- | :--- | :--- | :--- |
| **INV-1** | Contributions are non-negative ($S_A \ge 0, S_B \ge 0$). | `test_allocation_invariants_and_proportional_weighting` | **PASS** |
| **INV-2** | Exact sum conservation: $S_A + S_B \equiv F_{\text{shared}}$ in paise and Decimal. | `test_allocation_invariants_and_proportional_weighting` | **PASS** |
| **INV-3** | Proportional weighting: $F_A > F_B \implies S_A > S_B$. | `test_allocation_invariants_and_proportional_weighting` | **PASS** |
| **INV-4** | When $F_{\text{shared}} < F_A + F_B$, both passengers save money. | `test_allocation_invariants_and_proportional_weighting` | **PASS** |
| **INV-5** | When $F_{\text{shared}} == F_A + F_B$, `BREAK_EVEN` is reported and no savings are claimed. | `test_allocation_break_even_outcome` | **PASS** |
| **INV-6** | When $F_{\text{shared}} > F_A + F_B$, `UNATTRACTIVE` is reported with negative savings. | `test_allocation_dissavings_outcome` | **PASS** |
| **INV-7** | No fabricated savings in break-even or dissavings (`is_saving = False`, `savings_percent = 0.0`). | `test_allocation_dissavings_outcome` | **PASS** |
| **INV-8** | Rounding cannot create false savings claim in micro-fare edge cases. | `test_allocation_rounding_cannot_create_false_savings` | **PASS** |
| **INV-9** | Solo baseline estimates remain unchanged by allocation. | `test_allocation_invariants_and_proportional_weighting` | **PASS** |
| **INV-10** | Original shared trip fare remains unchanged by allocation. | `test_allocation_invariants_and_proportional_weighting` | **PASS** |
| **INV-11** | Driver's agreed gross fare is never reduced or discounted. | `test_allocation_invariants_and_proportional_weighting` | **PASS** |
| **INV-12** | Safe handling of negative, zero, and micro-fare inputs without exceptions or division errors. | `test_allocation_zero_and_invalid_inputs` | **PASS** |

---

## 2. Privacy & DEC-013 Consent Verification

| Test Case | Description | Test Outcome |
| :--- | :--- | :--- |
| **TEST-PRIV-01** | Co-passenger solo baseline is redacted from serialized proposal. | **PASS** |
| **TEST-PRIV-02** | Co-passenger contribution is `None` prior to bilateral consent. | **PASS** |
| **TEST-PRIV-03** | Co-passenger private savings are redacted in both unconsented and consented states. | **PASS** |
| **TEST-PRIV-04** | Bilateral consent reveals `co_passenger_contribution` such that $S_A + S_B == F_{\text{shared}}$. | **PASS** |

---

## 3. Frontend Presentation Verification

| Test Case | Component | Verification Goal | Outcome |
| :--- | :--- | :--- | :--- |
| **FE-ALLOC-01** | `MatchResults.tsx` | Clearly distinguishes Original shared fare, Solo baseline, and Allocated share. | **PASS** |
| **FE-ALLOC-02** | `MatchResults.tsx` | Renders savings badge and percentage savings when beneficial. | **PASS** |
| **FE-ALLOC-03** | `MatchResults.tsx` | Displays DEC-013 privacy notice and driver gross fare conservation. | **PASS** |

---

## 4. Test Execution Summary

```
backend/app/tests/test_fares.py: 37 passed
backend/app/tests/test_matching_phase5a.py: 24 passed
Full backend suite: 181 passed, 1 skipped
Frontend vitest suite: 32 passed
Total automated tests executed: 213 tests (100% passing)
```
