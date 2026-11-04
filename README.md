# Smart Share

> **Intelligent, Location-Based Cab Pooling**
>
> *"Same place. Same time. Compatible routes. One smarter shared ride."*

---

## 📖 About The Project

Smart Share is an intelligent, location-based cab pooling system built to solve a common and overlooked problem: people leaving the same venue travel along overlapping routes in separate cabs, resulting in empty seats, higher individual fares, and unnecessary traffic.

**The core gap** — Passengers lack a real-time, safe way to discover and coordinate with compatible co-travellers standing right beside them.

**The audience** — Event-goers, airport and station travellers, and daily commuters looking to split costs and reduce peak-hour cab wait times.

Unlike basic proximity-matching apps that simply group nearby passengers, Smart Share performs **journey-feasibility matching** — it enforces each passenger's maximum extra travel time, checks route compatibility, and shows transparent fare and savings estimates before anyone confirms.

---

## ✨ Features & Unique Selling Points

| Feature | Description |
| :--- | :--- |
| **Departure-aware matching** | Matches passengers by departure time window and route compatibility |
| **Detour-constrained ordering** | Enforces each passenger's maximum extra travel time per trip |
| **Transparent fare estimates** | Shows fare share, estimated savings, and extra travel time upfront |
| **Common-route compatibility** | Scores route overlap and travel-time suitability before proposing a pool |
| **Event-independent** | Works across events, stations, airports, and daily commutes |

---

## 🚦 How It Works

Smart Share guides a passenger through five clear steps:

1. **Create a trip** — Enter pickup location, destination, departure window, number of seats, and maximum acceptable extra travel time.
2. **Find compatible travellers** — The system filters by pickup proximity, overlapping departure times, and route fit.
3. **Build a feasible pool** — Vehicle capacity, pickup/drop-off order, and detour limits are all checked.
4. **Compare the proposal** — See the shared route, fare split, estimated savings, and extra travel time before committing.
5. **Confirm and coordinate** — Accept or decline the pool and receive updated group information.

---

## 🏗️ Technical Approach

### Architecture Overview

```
Passenger / Smartphone (Browser)
        │
        ▼
  React + Vite + TypeScript (Frontend)
        │
        ▼
  FastAPI Backend
  ├── Ride Request Service
  ├── Geospatial & Departure-Time Candidate Filtering
  ├── Route Compatibility & Matching Engine
  │       ├── Road Route / ETA Evaluation
  │       ├── Detour & Stop-Order Optimization
  │       └── Fare Estimation
  └── Routing Provider Adapter (openrouteservice)
        │
        ▼
  PostgreSQL + PostGIS (Database)
```

### Matching Methodology

The matching engine is **explainable and deterministic**. It follows these steps in order:

1. Filter candidates by pickup proximity and compatible departure windows.
2. Score route compatibility and travel-time suitability.
3. Enforce seat capacity and each passenger's maximum extra-travel-time limit.
4. Evaluate feasible pickup and drop-off sequences.
5. Estimate fare shares and savings.
6. Present the proposal for passenger acceptance.

> The MVP uses a heuristic approach for small groups. It is not claimed to be globally optimal and uses no unvalidated machine learning. Advanced optimisation can follow in later iterations.

### Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React · Vite · TypeScript · Tailwind CSS |
| **Backend** | Python · FastAPI · hosted API · managed PostgreSQL |
| **Data & Maps** | PostgreSQL + PostGIS (Supabase) · Leaflet + OpenStreetMap |
| **Routing** | openrouteservice (behind a replaceable adapter) |

---

## ✅ Feasibility & Viability

### Technical Feasibility

- **React + FastAPI** — a practical and proven web/API stack.
- **PostGIS** — enables efficient geographic candidate search.
- **Routing API** — provides road distances and ETAs.
- **Modular backend** — each service can be built and tested independently.
- **Event-based prototype** — validates the core algorithm before wider rollout.

### Key Challenges & Mitigations

| Challenge | Mitigation |
| :--- | :--- |
| Too few matching passengers | Start with event-based pools; demo on a controlled synthetic dataset |
| Poor route compatibility | Enforce maximum detour and extra-travel-time limits |
| Routing API limits or failures | Cache repeated requests where appropriate; keep a demo fallback |
| Cancellations and overbooking | Database transactions, capacity checks, and explicit group states |
| Safety and location privacy | Minimise stored data, restrict access, share only what is needed |

> **Viability boundary:** The initial deliverable is a functional pooling and coordination prototype. Real cab dispatch, guaranteed vehicle availability, payments, and driver integrations require separate integration work and are not assumed in this scope.

---

## 🌍 Impact & Benefits

| Area | Expected Benefit |
| :--- | :--- |
| **Economic** | Lower estimated per-passenger travel cost |
| **Utilisation** | Better use of available vehicle seats |
| **Social** | Easier coordination along compatible routes |
| **Environment** | Potentially fewer separate trips and vehicle-kilometres (to be measured) |
| **Clarity** | Visible trade-off between savings and extra travel time |

### Validation Metrics

The following metrics will be tracked during testing and piloting:

- Feasible match rate
- Estimated savings per matched passenger
- Extra passenger travel time
- Average group occupancy
- Successful group confirmations
- Avoided vehicle-km (if assumptions hold)

> **Note:** Pilot targets are proposals to be validated — not achieved results. Congestion and emission benefits are potential impacts to measure through testing, not proven outcomes.

---

## 🔬 Research & References

The design choices in Smart Share are grounded in published research and established documentation:

- **Agatz, N., Erera, A., Savelsbergh, M., & Wang, X. (2012).** *Optimization for dynamic ridesharing: A review.* European Journal of Operational Research, 223(2), 295–303. DOI: [doi.org/10.1016/j.ejor.2012.05.028](https://doi.org/10.1016/j.ejor.2012.05.028)
  *Surveys matching of riders with flexible times and routes — the core problem Smart Share's constraint-based matching addresses.*

- **React** — Frontend UI · [react.dev/learn](https://react.dev/learn)
- **FastAPI** — Python backend API · [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **Supabase Docs: PostGIS extension** — Geospatial candidate search · [supabase.com/docs/guides/database/extensions/postgis](https://supabase.com/docs/guides/database/extensions/postgis)
- **Leaflet** — Interactive map on OpenStreetMap tiles · [leafletjs.com](https://leafletjs.com)
- **openrouteservice API** — Road routes and ETA (via adapter) · [openrouteservice.org/dev/#/api-docs](https://openrouteservice.org/dev/#/api-docs)

> Sources support the planned design choices and are not performance claims for Smart Share.

---

## 👥 Team

**Team Name:** Terminal 1

**Hackathon:** NOVEX 2026 — Round 2

**Problem Statement Category:** Smart Automation

---

## 📝 License

This project was created for the NOVEX Hackathon 2026. Please refer to the competition guidelines for usage and distribution terms.
