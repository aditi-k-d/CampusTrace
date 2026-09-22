# CampusTrace — Methodology

## Guiding Principle

Build the smallest working vertical slice first (one user, one room, one contact, one alert), then expand horizontally (more users, more rooms, more features). Don't build the whole schema or every screen before testing a single BFS trace end-to-end — verify the pipeline works on a small case before scaling it up.

## Tech Stack and Why

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | React | Simple, component-based, no need for anything fancier for this scope |
| Backend | Flask (Python) | Fastest path to REST + MySQL + React integration for a 4-person team on a fixed deadline |
| Database | MySQL | Relational structure fits the domain well (users, timetables, enrollment, health records all have clear relational structure) |
| Core algorithms | Hand-written Python (no NetworkX) | This project is centered on DSA and algorithmic logic — using a library that hides BFS/Union-Find behind one function call would defeat the purpose. Every core algorithm (Graph, BFS/DFS, Union-Find, priority queue/heap) is implemented from scratch so the logic is fully explainable in a viva |



## Core Algorithms Used

| Algorithm / Data Structure | Used for |
|---|---|
| Graph (adjacency list, weighted, undirected) | Representing the contact network — nodes are users, edges are shared presence |
| BFS / DFS (forward direction) | Tracing who an infected person may have exposed |
| BFS / DFS (backward direction) | Tracing who may have exposed the infected person — informed by network-theory literature on backward tracing effectiveness |
| Union-Find (Disjoint Set, with path compression) | Detecting outbreak clusters — grouping mutually connected high-risk contacts |
| Priority Queue / Heap | Ranking contacts by risk score for testing/isolation prioritization when capacity is limited |
| Sliding window / exponential decay | Time-decayed exposure risk — a contact from 5 days ago matters less than one from yesterday |
| Weighted scoring formula | Combining duration, recency, and room-type into a single graded risk score (Low/Medium/High) |

Tracing depth and direction (forward vs backward, how many degrees of contact) are kept **configurable per outbreak** rather than hardcoded — recent literature (Juul & Strogatz, 2023) shows that which strategy is more effective is context-dependent, not universal.

## Phased Roadmap

### Phase 1 — Foundation (Weeks 1–5)
- Finalize and commit database schema
- Auth & role-based access control (RBAC) — 5-tier role system
- Core DSA modules built and unit-tested in isolation (Graph, BFS/DFS, Union-Find, heap, risk scorer)
- API contract documented — every endpoint other members will call, defined up front
- Single division (CS-C) timetable and structure seeded manually through the admin interface as it's built (no synthetic/random seed data)

### Phase 2 — Core Data Pipeline (Weeks 6–9)
- Student registration flow (division → batch selection for lab/tutorial courses only)
- Nightly/on-demand batch job: TimetableSlot + Enrollment → Presence records
- Contact graph builder: Presence records → weighted Edges
- A second division introduced once the single-division pipeline is verified, to enable and test faculty cross-division bridging

### Phase 3 — Reporting & Tracing (Weeks 10–13)
- Student self-report (disease/symptoms, onset date, severity) and faculty absence-flagging (with confirm/deny state machine)
- Disease Knowledge Base seeded with real known conditions (chickenpox, flu, etc.) and their symptoms/preventive measures
- Forward + backward tracing implemented and tested against the contact graph
- Risk scoring engine applied to traced contacts

### Phase 4 — Dashboards & Response (Weeks 14–17)
- Role-specific dashboards (student alerts, faculty class-status view, health admin cluster/hotspot view, institute admin aggregated view)
- K-anonymity thresholding applied to all aggregate/admin views
- Isolation/health-center capacity tracker with priority-queue based allocation
- Self-assessment (rule-based triage) interface

### Phase 5 — Evaluation & Hardening (Weeks 18–20)
- Feedback loop: flagged false positives adjust future risk weights
- End-to-end testing: seed a test case, verify tracing/alerts/dashboards work correctly together
- Audit logging for Institute Admin oversight
- Async background tracing: move synchronous health-report tracing to an asynchronous background job queue (e.g., Celery/Redis) for production-scale institution deployment
- Evaluation metrics: precision/recall of exposure detection against a known ground-truth test case, alert latency
- Final documentation, report, and demo preparation

## Evaluation Approach

Since this is a pilot on real (not synthetic) data, evaluation focuses on:
- **Correctness:** does tracing correctly identify all true contacts of a seeded test case, given the known timetable/enrollment data?
- **Latency:** how quickly does an alert reach a contact after a case is reported?
- **Privacy compliance:** do aggregate views correctly suppress data below the k-anonymity threshold?
- **Cross-division bridging (once Phase 2's second division is added):** does a faculty member teaching both divisions correctly appear as a bridge node connecting two otherwise-separate clusters?

## What This Methodology Deliberately Avoids

- No BLE/GPS proximity sensing — all contact data comes from structured institutional records
- No black-box ML for risk scoring — the formula is explainable and rule-based (a feedback-driven weight adjustment is the only place a simple learning mechanism might be introduced, and only as a later addition)
- No synthetic/seeded fake data — real data is entered by actual users (admin adds timetables, students register and select batches) as the system comes online
- No unnecessary infrastructure — no Docker, no cloud deployment, no external third-party APIs