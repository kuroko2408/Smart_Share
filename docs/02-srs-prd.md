# Smart Share — Software Requirements Specification and Product Requirements Document

**Document:** SRS / PRD  
**Version:** 1.0  
**Status:** Initial Draft — Pending Review  
**Project:** Smart Share — Intelligent, Location-Based Cab Pooling

---

## 1. Introduction

### 1.1 Purpose

This document defines the functional and non-functional requirements of Smart Share. It establishes the expected behaviour of the platform, the requirements of its users and the acceptance criteria that will guide development and testing.

It serves as a reference for frontend development, backend development, database design, matching-engine implementation and quality assurance.

### 1.2 Product Description

Smart Share is a mobile-first platform that allows users with compatible pickup locations, destinations and departure times to form shared-ride groups.

The system evaluates potential combinations using geographical proximity, time compatibility, route compatibility, available passenger capacity and acceptable detours.

The platform initially coordinates passenger matching. It does not guarantee a real cab, driver or transportation service.

### 1.3 Intended Audience

- Project developers.
- UI/UX designers.
- Testers.
- Hackathon evaluators.
- Future contributors.

### 1.4 Definitions

| Term | Meaning |
|---|---|
| Ride Request | A user's request to travel between two locations |
| Pickup Point | Location where a passenger wants to begin the journey |
| Destination | Location where a passenger wants to end the journey |
| Departure Window | Earliest and latest acceptable departure times |
| Candidate | Another ride request being evaluated for compatibility |
| Match | A proposed combination of compatible ride requests |
| Ride Group | A collection of passengers associated with a shared journey proposal |
| Detour | Additional journey distance or time caused by accommodating other passengers |
| Routing Provider | External service used to estimate road routes and travel times |
| Pooled Fare | Estimated total cost of the shared journey |
| Individual Share | Estimated amount allocated to a passenger |

---

## 2. Product Goals

Smart Share aims to:

1. Reduce the cost of individual cab journeys.
2. Improve passenger capacity utilization.
3. Make passenger coordination easier.
4. Minimize unnecessary route deviations.
5. Provide transparent fare estimates.
6. Make matching decisions explainable.
7. Support multiple use cases beyond organized events.

## 3. User Personas

### 3.1 Student Leaving a College Event

A student is leaving a college festival at approximately 10:30 PM. They want to travel home and would prefer to share a cab with other students travelling in a similar direction.

Needs:
- Quick ride request creation.
- Compatible passengers.
- Low additional travel time.
- Clear estimated fare.

### 3.2 Passenger Leaving an Airport

A passenger arriving at an airport wants to share a cab with others travelling towards nearby areas.

Needs:
- Accurate pickup location.
- Flexible departure time.
- Destination compatibility.
- Transparent cost estimates.

### 3.3 Office Commuter

An employee travels from the same office district every evening and wants to discover other commuters travelling along a similar route.

Needs:
- Simple request creation.
- Time-window compatibility.
- Repeatable journey preferences as a possible future feature.

---

## 4. System Overview

The system consists of:

1. Frontend application.
2. Backend API.
3. Authentication service.
4. PostgreSQL/PostGIS database.
5. Matching engine.
6. Routing service integration.
7. Fare calculation service.
8. Notification and group-management services.

### 4.1 High-Level User Workflow

1. User opens Smart Share.
2. User signs in.
3. User enters pickup and destination.
4. User selects an acceptable departure window.
5. User specifies required seats and maximum additional travel time.
6. User submits a ride request.
7. Backend validates and stores the request.
8. Matching engine discovers candidate requests.
9. Routing service evaluates road-route compatibility.
10. Matching engine constructs feasible groups.
11. System calculates estimated fare distribution.
12. User receives proposed match information.
13. User accepts or declines the proposal.
14. The group and membership state are updated.
15. User can view the current group status.

---

## 5. Functional Requirements

Priority definitions:

- **P0:** Essential for the MVP.
- **P1:** Important, but may follow the basic workflow.
- **P2:** Future enhancement.

### FR-01: User Authentication — P0

The system shall allow users to authenticate using the configured authentication provider.

Requirements:

- Users must have an authenticated session before creating or modifying personal ride requests.
- The backend must validate authentication tokens.
- The system must associate each request with the authenticated user.
- Users must not be able to access another user's private information without authorization.

Acceptance criteria:

- An unauthenticated request to a protected endpoint is rejected.
- An authenticated user can retrieve their own profile.
- A user cannot impersonate another user by supplying a different user ID.

### FR-02: User Profile — P1

The system shall maintain basic user profile information.

Possible fields:

- Display name.
- Profile image URL.
- Contact information, if required.
- Account creation timestamp.

Sensitive contact details must not be exposed unnecessarily.

### FR-03: Location Selection — P0

The system shall allow users to select pickup and destination locations.

Requirements:

- Users can search for a location.
- Users can select a map location where supported.
- The system stores latitude and longitude.
- The system may store a human-readable location label.
- Invalid coordinates must be rejected.

Acceptance criteria:

- A valid pickup and destination can be selected.
- Coordinates are persisted correctly.
- Invalid coordinate values are rejected.

### FR-04: Ride Request Creation — P0

The system shall allow authenticated users to create a ride request.

Required information:

- Pickup coordinates.
- Destination coordinates.
- Earliest departure time.
- Latest departure time.
- Number of seats required.
- Maximum acceptable additional travel time.

Validation rules:

- Latitude must be between -90 and 90.
- Longitude must be between -180 and 180.
- Latest departure must not be earlier than earliest departure.
- Seats requested must be a positive integer.
- Maximum additional travel time must be non-negative and within the configured system limit.
- Past departure windows must be rejected or handled according to an explicit expiry policy.

Acceptance criteria:

- Valid requests are stored.
- Invalid requests return validation errors.
- A request is associated with the authenticated user.

### FR-05: Ride Request Management — P0

Users shall be able to:

- View their active requests.
- View an individual request.
- Update eligible request fields.
- Cancel their own request.

A request that has already joined a confirmed group must follow the group cancellation rules.

### FR-06: Candidate Discovery — P0

The system shall identify candidate requests using:

- Pickup-location proximity.
- Departure-window compatibility.
- Request status.
- Request expiry.
- Seat availability.
- Existing group membership.

Only eligible requests shall proceed to detailed route evaluation.

### FR-07: Time Compatibility — P0

The system shall evaluate whether two or more users can depart within compatible time windows.

Two requests are time-compatible when their permitted departure windows overlap sufficiently for the configured coordination policy.

The exact departure-time selection must be feasible for all members.

The system must not match users merely because their departure times are close if their acceptable windows do not permit a shared departure.

### FR-08: Route Compatibility — P0

The system shall evaluate whether passengers can reasonably share a road journey.

Requirements:

- Evaluate road-route distance and duration.
- Consider pickup and drop-off order.
- Calculate additional journey time for passengers.
- Reject groups that exceed configured detour limits.
- Avoid treating straight-line geographical distance as road distance.

### FR-09: Group Formation — P0

The matching engine shall construct feasible groups.

Requirements:

- A request must not be assigned to multiple active groups.
- Group capacity must not be exceeded.
- Each member's seat requirement must be respected.
- Adding a passenger must not invalidate the group's route constraints.
- Candidate groups must be ranked.
- The matching process must be reproducible for the same inputs and algorithm version where external routing results are unchanged.

### FR-10: Match Proposal — P0

The system shall display:

- Proposed group members or appropriate participant information.
- Pickup and drop-off sequence.
- Estimated shared journey time.
- Estimated individual additional travel time.
- Estimated total fare.
- Estimated fare contribution.
- Estimated savings.
- Match expiry or response deadline, where applicable.

The system must clearly label estimated values.

### FR-11: Accept or Decline a Match — P0

Users shall be able to accept or decline a match proposal.

Requirements:

- Only eligible members can respond.
- Repeated requests must be handled safely.
- Expired proposals cannot be accepted.
- Acceptance must not violate seat capacity.
- A request cannot join multiple active groups.

### FR-12: Ride Group Management — P0

The system shall provide group details and lifecycle status.

Initial group statuses:

- `PROPOSED`
- `CONFIRMED`
- `IN_PROGRESS`
- `COMPLETED`
- `CANCELLED`
- `EXPIRED`

The exact allowed transitions must be enforced by the backend.

### FR-13: Cancellation — P0

Users shall be able to cancel eligible ride requests or withdraw from groups according to the group's current state.

The system must:

- Prevent invalid cancellation transitions.
- Update group membership.
- Release reserved capacity where appropriate.
- Re-evaluate or cancel affected proposals.
- Preserve historical records.

### FR-14: Notifications — P1

The system should inform users about:

- New match proposals.
- Match acceptance.
- Match rejection.
- Group confirmation.
- Cancellation.
- Relevant status changes.

The initial implementation may use in-app status updates before introducing external push notifications.

### FR-15: Map Visualization — P1

The system should display:

- Pickup locations.
- Destination locations.
- Proposed route.
- Intermediate pickup and drop-off stops.

The map must not imply live vehicle tracking unless that capability is implemented.

### FR-16: Demo Data — P0

The system shall support a reproducible synthetic dataset for demonstration and testing.

The dataset should include:

- Compatible requests.
- Incompatible departure windows.
- Distant pickup locations.
- Similar destinations.
- Excessive detour cases.
- Capacity conflicts.
- Cancellation cases.

---

## 6. Non-Functional Requirements

### NFR-01: Performance

- Normal API requests should respond promptly under the expected demo load.
- Matching operations should avoid unnecessary routing-provider calls.
- Candidate discovery should use database indexes.
- Performance targets must be measured using a documented test dataset.

Initial target for testing: complete a typical demo matching operation within 5 seconds for a small dataset, excluding unusually slow external routing-provider responses.

### NFR-02: Reliability

- Database transactions must protect group membership and seat allocation.
- External routing failures must not crash the entire application.
- Invalid requests must not partially update group state.
- The application must handle duplicate requests safely.

### NFR-03: Security

- Protected endpoints require authentication.
- Users can access only authorized resources.
- Secrets must be stored in environment variables or a secrets manager.
- Frontend code must never contain privileged database credentials.
- Input validation must be performed on the backend.
- Database queries must use parameterized ORM operations.

### NFR-04: Privacy

- Collect only information required for the service.
- Do not expose exact user locations to unrelated users.
- Avoid unnecessary retention of sensitive location history.
- Use HTTPS in deployed environments.
- Define an appropriate data-retention policy before production use.

### NFR-05: Usability

- The primary ride-request flow should be straightforward.
- Forms should provide clear validation messages.
- Estimated fares and savings should be easy to understand.
- Users should understand that a match proposal is not a confirmed cab booking.

### NFR-06: Maintainability

- Separate frontend features into reusable modules.
- Separate backend business logic from API controllers.
- Keep matching and routing logic independently testable.
- Use database migrations.
- Maintain API and architecture documentation.

### NFR-07: Portability

The application should be deployable using standard web-hosting and database services without depending on a single developer's local environment.

---

## 7. Business Rules

1. A ride request must belong to one authenticated user.
2. A user cannot reserve more seats than the configured vehicle capacity.
3. A group cannot exceed its capacity.
4. A request cannot participate in multiple active groups.
5. Departure windows must permit a common feasible departure.
6. Every member must satisfy the configured route-detour constraint.
7. A proposed match is not equivalent to a booked cab.
8. Fare values are estimates until a real transport provider supplies a confirmed price.
9. Cancelled and expired requests cannot be used for new matching.
10. All group-state transitions must be validated by the backend.

---

## 8. Matching Requirements

The matching engine shall use multiple stages.

### Stage 1: Candidate Filtering

Filter requests using:

- Pickup proximity.
- Departure-window overlap.
- Active status.
- Request expiry.
- Available capacity.
- Existing group eligibility.

### Stage 2: Detailed Route Evaluation

For each promising candidate combination:

- Obtain road-route estimates.
- Evaluate pickup/drop-off order.
- Calculate route duration.
- Calculate passenger-specific detours.
- Reject infeasible combinations.

### Stage 3: Compatibility Scoring

An initial configurable scoring model is proposed:

`Score = 0.20P + 0.15T + 0.35R + 0.30E`

Where:

- `P` = pickup proximity score.
- `T` = departure-time compatibility score.
- `R` = route compatibility score.
- `E` = travel efficiency and estimated savings score.

Each component is normalized between 0 and 1.

These weights are initial assumptions and must be evaluated against test scenarios. Hard constraints must be checked separately; a high score must never override a capacity or detour violation.

### Stage 4: Group Construction

Use a deterministic greedy heuristic initially:

1. Select a promising candidate group.
2. Consider adding another compatible request.
3. Recalculate capacity and route feasibility.
4. Keep the addition only if all constraints remain satisfied.
5. Evaluate small-group stop sequences.
6. Rank feasible groups.

The system must not claim that the heuristic always produces a globally optimal route or group.

---

## 9. Fare Calculation Requirements

The system shall calculate:

- Estimated individual journey cost.
- Estimated shared journey cost.
- Estimated contribution for each passenger.
- Estimated savings for each passenger.

Formula:

`Estimated Savings = Individual Estimate - Pooled Fare Share`

The fare-allocation policy must be documented. A distance-based or hybrid allocation policy may be considered so passengers travelling different distances are not automatically charged equally.

The initial MVP may use configurable estimates rather than live cab fares.

---

## 10. User Interface Requirements

The application should include these principal screens:

1. Landing / Welcome.
2. Authentication.
3. Home / Ride Search.
4. Pickup and Destination Selection.
5. Ride Request Form.
6. Finding Matches.
7. Match Results.
8. Match Details.
9. Ride Group Details.
10. User Profile.
11. My Requests / Ride History.

The exact layout and visual system will be defined in a separate UI/UX design process after the requirements and architecture are approved.

---

## 11. Error Handling

The system must provide understandable errors for:

- Invalid coordinates.
- Invalid departure windows.
- No compatible matches.
- Routing-provider unavailability.
- Expired proposals.
- Unauthorized access.
- Duplicate acceptance.
- Capacity conflicts.
- Cancelled requests.
- Missing resources.

Errors must not expose stack traces, database credentials or sensitive internal details.

---

## 12. Acceptance Criteria for MVP

The MVP is acceptable when:

- A user can authenticate.
- A user can create and cancel a ride request.
- Ride requests are persisted correctly.
- Candidate requests are filtered by geography and time.
- Route feasibility is evaluated.
- Over-capacity groups are rejected.
- Excessive detours are rejected.
- Feasible groups can be proposed.
- Fare estimates can be displayed.
- Users can accept or decline proposals.
- Concurrent acceptance cannot overbook a group.
- Group lifecycle transitions are validated.
- The primary workflow can be demonstrated using synthetic data.
- Critical backend and frontend tests pass.

---

## 13. Future Enhancements

Potential future features include:

- Recurring commute requests.
- Event-based ride coordination.
- Group chat.
- Verified user profiles.
- Driver and vehicle integration.
- Real cab-provider APIs.
- Live trip tracking.
- Payment integration.
- Ratings and feedback.
- More advanced optimization algorithms.
- Predictive demand analysis.

These features are not part of the initial MVP unless formally added to the scope.

---

## 14. Open Questions

The following decisions require team confirmation:

1. Maximum vehicle capacity for the MVP.
2. Default pickup-radius threshold.
3. Maximum additional travel-time threshold.
4. Whether users can edit requests after a match proposal is created.
5. Whether all group members must accept before confirmation.
6. Match proposal expiry duration.
7. Fare-allocation policy.
8. Whether event association is included in the first frontend version.
9. Routing provider and its usage limits.
10. Whether notifications are in-app only or include email/push.

**Document Status:** Initial Draft — Requirements must be reviewed before implementation.