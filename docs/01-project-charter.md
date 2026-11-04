# Smart Share — Project Charter

**Project Name:** Smart Share  
**Project Subtitle:** Intelligent, Location-Based Cab Pooling  
**Project Type:** Hackathon Project / Software Engineering Project  
**Project Stage:** Planning and Documentation  
**Version:** 1.0 — Initial Draft  
**Status:** Proposed — Pending Team Review

---

## 1. Project Overview

Smart Share is a mobile-first, location-aware cab-pooling platform designed to connect people travelling from the same or nearby pickup locations to the same or nearby destinations within compatible departure time windows.

In everyday situations, people leaving concerts, college events, weddings, railway stations, airports, offices and other crowded locations often book separate cabs despite having similar travel routes. This results in unnecessary individual travel expenses, underutilized vehicle capacity and additional traffic.

Smart Share aims to address this problem by intelligently identifying compatible ride requests and proposing groups of passengers who can share a journey while keeping additional travel time and route deviations within acceptable limits.

The platform focuses on **matching passengers and coordinating shared journeys**. It is not initially intended to operate as a cab company, dispatch drivers or guarantee vehicle availability.

## 2. Problem Statement

People travelling from the same or nearby locations at approximately the same time frequently book separate cabs because they lack an efficient way to discover other passengers travelling in similar directions.

Existing informal coordination methods, such as messaging groups and personal contacts, are unreliable and require manual effort. Passengers may be unaware of compatible travellers, and even when they find potential travel partners, they cannot easily evaluate route compatibility, detours, fare distribution or time savings.

This leads to:

- Higher individual transportation costs.
- Unused passenger capacity in vehicles.
- Increased number of separate cab journeys.
- Additional traffic around crowded venues and transport hubs.
- Difficulty coordinating departure times and pickup arrangements.

## 3. Project Vision

To make shared urban transportation more accessible by intelligently connecting people with compatible journeys, reducing individual travel costs and improving the utilization of available vehicle capacity.

## 4. Project Objectives

The primary objectives are:

1. Allow users to create ride requests with pickup locations, destinations, departure windows and passenger requirements.
2. Discover other active requests with geographically and temporally compatible journeys.
3. Evaluate compatibility using pickup proximity, departure-time overlap, route similarity, vehicle capacity and additional travel time.
4. Generate feasible passenger groups and propose an efficient pickup/drop-off sequence.
5. Display estimated shared fare, individual fare contribution and potential savings.
6. Allow users to accept or decline proposed groups.
7. Support ride-group status updates, cancellations and membership changes.
8. Provide a reliable, testable prototype suitable for a hackathon demonstration.

## 5. Target Users

### Primary Users

- Students leaving college events or campus.
- Concert and event attendees.
- People travelling from railway stations and airports.
- Office commuters.
- Wedding and social-event attendees.
- Individuals travelling along frequently used urban routes.

### Secondary Stakeholders

- Event organizers.
- College administrations.
- Communities coordinating group travel.
- Potential future cab-service or mobility partners.

## 6. Proposed Solution

Smart Share will provide a platform where users can:

1. Enter a pickup location and destination.
2. Select an earliest and latest acceptable departure time.
3. Specify the number of seats required.
4. Set their maximum acceptable additional travel time.
5. Submit a ride request.
6. Receive compatible shared-ride proposals.
7. Review proposed routes, pickup/drop-off order, estimated fares and savings.
8. Accept or decline a proposal.
9. View the status of their shared ride group.

The matching engine will use geographic filtering and road-route information to identify feasible combinations. It will prioritize practical shared journeys rather than simply matching people based on nearby locations.

## 7. Project Scope

### 7.1 In Scope — Initial MVP

- User authentication.
- Basic user profiles.
- Pickup and destination selection.
- Ride request creation, viewing, updating and cancellation.
- Departure-time windows.
- Seat requirements.
- Maximum additional travel-time preferences.
- Geographic candidate discovery.
- Time compatibility evaluation.
- Route compatibility evaluation.
- Passenger group formation.
- Pickup and drop-off sequence generation.
- Estimated fare calculation.
- Estimated individual savings.
- Match acceptance and rejection.
- Ride-group and membership management.
- Basic notifications or status updates.
- Map-based visualization.
- Synthetic demo data.
- Backend and frontend testing.
- Deployment of a demonstrable prototype.

### 7.2 Out of Scope — Initial MVP

The following features are not guaranteed or planned for the first version:

- Operating a real taxi fleet.
- Driver registration and driver applications.
- Automatic driver assignment.
- Direct cab-provider dispatch.
- Guaranteed vehicle availability.
- Online payments or wallet functionality.
- Live driver GPS tracking.
- Insurance or emergency-response services.
- Complex surge-pricing integration.
- Production-scale commercial operations.
- AI/ML-based predictions without a separately validated model.

These may be considered in future versions.

## 8. Proposed Technology Stack

The following is the proposed initial stack and may be revised through documented architecture decisions.

| Layer | Proposed Technology |
|---|---|
| Frontend | React + Vite + TypeScript |
| Styling | Tailwind CSS |
| UI Components | shadcn/ui |
| Frontend Routing | React Router |
| Server State | TanStack Query |
| Form Validation | Zod |
| Backend | Python + FastAPI |
| Data Validation | Pydantic |
| ORM | SQLAlchemy 2 |
| Database Migrations | Alembic |
| Database | PostgreSQL + PostGIS |
| Authentication | Supabase Auth |
| Maps | Leaflet |
| Map Data | OpenStreetMap-compatible provider |
| Road Routing | Replaceable routing-provider adapter |
| Backend Testing | Pytest |
| Frontend Testing | Vitest |
| End-to-End Testing | Playwright |
| Frontend Deployment | Vercel or equivalent |
| Backend Deployment | Render or equivalent |
| Database Hosting | Supabase |

## 9. Initial Success Criteria

The prototype will be evaluated against measurable pilot targets. These are goals to test, not achieved results.

| Metric | Initial Target |
|---|---:|
| Eligible requests successfully matched | At least 30% |
| Estimated passenger cost savings | At least 20% |
| Additional travel time | No more than 10 minutes where feasible |
| Synthetic or pilot requests evaluated | At least 100 |
| Core user journey | Fully demonstrable |
| Critical matching scenarios | Covered by automated tests |

The team must document the calculation method and dataset used for each metric.

## 10. Key Constraints and Assumptions

### Constraints

- Limited hackathon development time.
- Small development team.
- Dependence on external map and routing services.
- API usage limits and potential service costs.
- Accuracy limitations of estimated fares.
- Need to protect user location and personal information.

### Assumptions

- Users provide reasonably accurate pickup and destination information.
- Users specify realistic departure windows.
- A routing provider can supply road-distance and travel-time estimates.
- The MVP can use simulated ride requests to demonstrate matching.
- Actual cab booking and dispatch are outside the initial scope.

## 11. Major Risks

| Risk | Mitigation |
|---|---|
| Poor matching results | Test with varied datasets and refine compatibility rules |
| Excessive route detours | Enforce maximum additional travel-time constraints |
| Routing API failure | Use an adapter and provide graceful fallback behaviour |
| Concurrent seat reservations | Use database transactions and consistency constraints |
| Incorrect fare estimates | Clearly label estimates and document fare assumptions |
| Insufficient demo users | Prepare a reproducible synthetic dataset |
| Scope expansion | Freeze MVP scope and track future features separately |
| Privacy concerns | Minimize collected data and restrict access to user information |

## 12. Team Structure and Responsibilities

The proposed team has two developers.

### Developer A — Frontend and Product Experience

Responsible for:

- Frontend architecture.
- UI/UX implementation.
- Location and map interface.
- Ride request creation.
- Match proposal interface.
- Ride-group interface.
- API integration.
- Frontend testing.

### Developer B — Backend and Matching Engine

Responsible for:

- Backend architecture.
- Database schema and migrations.
- Authentication integration.
- Ride request APIs.
- Geospatial candidate discovery.
- Matching algorithm.
- Routing and fare calculations.
- Ride-group lifecycle.
- Backend testing.

### Shared Responsibilities

Both developers will participate in:

- Architecture decisions.
- API contract reviews.
- Integration testing.
- Code reviews.
- Documentation updates.
- Demo preparation.
- Final validation.

## 13. Project Deliverables

1. Approved project documentation.
2. Database schema and migrations.
3. Backend API.
4. Matching engine.
5. Frontend application.
6. Map and route visualization.
7. Automated test suite.
8. Synthetic demonstration dataset.
9. Deployment configuration.
10. Final project presentation and demonstration.

## 14. Project Governance

- All major architectural decisions must be documented.
- Changes to project scope require team agreement.
- The `main` branch must contain stable code.
- Features should be developed on separate branches.
- API changes must be reflected in the API contract documentation.
- Database changes must be implemented through migrations.
- Secrets and credentials must never be committed to Git.
- Documentation must be updated when implementation decisions change.

## 15. Definition of Project Success

The project will be considered successful when a user can create a ride request, the system can identify and explain compatible ride combinations, users can review and respond to proposed groups, and the complete workflow can be demonstrated reliably using test or synthetic data.

The prototype must demonstrate meaningful route-aware passenger matching rather than simple proximity-based grouping.

---

**Document Status:** Initial Draft  
**Next Review:** Before finalizing the SRS/PRD  
**Approval Required From:** Both project developers