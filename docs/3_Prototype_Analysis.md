# CampusTrace — Prototype Analysis

## 1. Summary

The CampusTrace prototype is a fully implemented, verified-from-source Flask + MySQL (SQLite-capable in dev) backend paired with a React + Vite frontend. Every route file, service, model, and dashboard listed in the project's task breakdown is present and matches the documented API contract — nothing in the plan remains unbuilt. The system converts a college division's timetable and enrollment data into a daily weighted contact graph (`presence_builder.py` → `graph_builder.py`), and when a student self-reports illness or a faculty member flags a health-related absence, it synchronously runs forward and/or backward BFS/DFS tracing over that graph (`tracing_service.py`), scores every traced contact with a transparent, fully arithmetic risk formula (`risk_engine.py`), generates role-appropriate alerts (`alert_service.py`), and surfaces all of this through five distinct role-scoped dashboards. Isolation-bed capacity is managed through a hand-written priority queue (`capacity_service.py`), and a Disease Knowledge Base with simple Jaccard-style symptom matching (`disease_kb_service.py`) supports both case classification and a non-diagnostic student self-assessment tool.

Roughly 6,892 lines of backend Python (~250 KB) and 1,600 lines of React (~90 KB) implement this end to end, on top of a 259-line relational schema — about 8,750 lines total. The pipeline is validated by a five-scenario integration test suite that walks a seeded case from timetable → presence → contact edge → health report → trace → alert → dashboard, verifying each stage against known ground truth rather than noisy real data. Zero device-level sensing code exists anywhere in the codebase — a full repository search for `BLE`, `GPS`, `Wi-Fi`, and `Bluetooth` returns no matches; every contact is derived purely from structured institutional records. A source-code-level review also surfaced concrete, specific weaknesses — a capacity-allocation race condition, several hardcoded thresholds, and a missing transaction-rollback trap in alert generation — which are detailed below rather than glossed over.

## 2. In-Depth Working

### 2.1 Data foundation: from timetable to presence

`presence_builder.build_presence_for_date(target_date: date_cls, session=None) -> int` is the pipeline's entry point. For the given date, it looks up every `TimetableSlot` scheduled for that weekday, determines who is expected to attend (enrolled students plus assigned faculty for that course/batch), and inserts a `Presence` row for each attendee who doesn't already have one for that slot+date. The function is **idempotent by design** — it computes a set difference against existing DB records before inserting, so re-running it never duplicates data. This is the layer that turns static institutional structure (who is enrolled in what, when) into a dynamic daily record of who was where.

### 2.2 From presence to contact edges

`graph_builder.build_edges_for_date(target_date: date_cls, session=None) -> int` queries that day's `Presence` rows, groups them in memory by `(room_id, slot_id)`, and for every group of two or more co-present people runs `itertools.combinations(group, 2)` to generate every pairwise contact. Each resulting `ContactEdge` is stamped with a `room_type_weight` (1.20 lab, 1.10 tutorial, 1.0 theory), and a uniqueness check on `(user_a, user_b, date, room)` prevents duplicate edges. This is the step that actually materializes the "contact graph" the rest of the system reasons over — nodes are users, edges are shared classroom/lab presence, weighted by both duration and setting.

### 2.3 The tracing pipeline

`tracing_service.trace_case(health_record, direction=None, max_depth=None) -> dict` is invoked from a health report or absence flag. It first pulls every `ContactEdge` touching the index case's `user_id`, then filters by date relative to onset: **backward** tracing keeps edges where `contact_date < onset_date` (looking for a possible source); **forward** tracing keeps edges where `contact_date >= onset_date` (looking for who the case may have exposed). This filtered edge set is handed to `graph/traversal.py`'s depth-bounded BFS/DFS, which walks outward up to `max_depth` hops (default 2), accumulating a cumulative path weight per reached user and generating a dictionary of connected users scored by depth and path weight. The output is reshaped into a `vis-network`-compatible node/edge JSON payload for direct rendering on the Health Admin dashboard.

### 2.4 Risk scoring

`risk_engine.compute_contact_risk(duration_minutes, days_since_contact, room_weight) -> float` is pure arithmetic — no machine learning, entirely explainable and auditable:

```
duration_component = min(max(duration_minutes, 0) / 120, 1.0)
recency_component  = exp(-0.15 * max(days_since_contact, 0))
score = duration_component * recency_component * room_type_weight
return max(0.0, min(score, 1.0))
```

- **Duration component:** capped at 120 minutes, so additional shared time beyond two hours doesn't keep inflating the score.
- **Recency component:** an exponential decay (rate 0.15/day), so a contact from yesterday scores meaningfully higher than one from a week ago, without a hard cliff.
- **Room-type weight:** 1.20 for labs, 1.10 for tutorials, 1.0 for theory — hardcoded at the top of `graph_builder.py`.

When the same pair has multiple contact events, individual scores are combined via **Noisy-OR** aggregation — `1 − Π(1 − score_i)` — treating each contact as an independent chance of transmission, correctly keeping the combined probability bounded below 1.0 rather than letting per-contact scores simply sum past 100%.

### 2.5 Alert generation and delivery

`alert_service.generate_alerts(health_record, traced_contacts, session=None) -> list[Alert]` merges forward and backward trace results; where a user appears in both, it deduplicates by keeping the higher risk score. It looks up matching symptoms from the Disease Knowledge Base where the case is disease-confirmed, falling back to the reporter's custom symptom text otherwise, and writes an `Alert` row per exposed user with the computed risk level and a **denormalized `symptoms_snapshot`** — meaning even if the KB entry is later edited, an alert already delivered stays historically accurate to what the student actually saw.

### 2.6 Isolation capacity allocation

`capacity_service.allocate_highest_priority(capacity: Capacity) -> IsolationAllocation | None` calls `build_waiting_queue()`, which scans all unacknowledged `Alert` rows, returning the maximum risk score per user who lacks an active `IsolationAllocation`. These are pushed into a hand-written `PriorityQueue`. If the facility isn't full, the highest scorer is popped, `capacity.occupied_beds` is incremented, and the allocation is created and returned — a direct, working implementation of risk-score-driven prioritization for a genuinely scarce resource.

### 2.7 Symptom-based disease suggestion

`disease_kb_service.suggest_disease(custom_symptoms: str) -> Optional[DiseaseKB]` tokenizes incoming text into lowercase alphabetic words, tokenizes every `DiseaseKB` entry's symptom list the same way, and computes a Jaccard-style recall score (`overlap / len(query_tokens)`), returning the highest-scoring disease above `MATCH_MIN_SCORE` (hardcoded at 0.20). This powers both the Health Admin case-classification workflow and the student self-assessment triage tool.

### 2.8 Database schema (verified from `schema.sql`)

The schema is strictly relational (InnoDB, foreign keys, indexes): `divisions` (id, name, branch, year), `rooms` (id, name, building, capacity), `courses` (id, division_id FK-CASCADE, course_type ENUM theory/lab/tutorial), `users` (id, role ENUM across 5 roles, division_id FK-SET-NULL), `timetable_slots` (course_id FK-CASCADE, room_id FK-RESTRICT, batch_id FK-CASCADE, start/end time), `presence` (unique on user_id+slot_id+presence_date), `contact_edges` (unique per user-pair+date+room, stores duration_minutes and room_type_weight as DECIMAL(4,3)), `alerts` (FK to users and health_records, risk_level ENUM, risk_score DECIMAL(5,2), denormalized symptoms_snapshot), and `system_config` — a deliberately singleton table (`CHECK (id = 1)`) holding tunables like `k_anonymity_threshold` (default 5).

### 2.9 Frontend architecture

Built on React + Vite, all five dashboards use `useState`/`useEffect` with a shared `axios` client (`api/client.js`) that injects the JWT on every request. `StudentDashboard.jsx` tracks `loading`, `courses`, `alerts`, `healthRecords` and fires GETs for each plus a POST on report submission. `InstituteAdminDashboard.jsx` is the most complex, managing a tabbed interface (`activeTab`, `aggregates`, `departmentStats`, `config`, `usersList`, plus per-form state for divisions/rooms) firing multiple parallel GETs in `useEffect` for the various k-anonymized dashboard endpoints, and POSTs on each tab's form submission. `HealthAdminDashboard.jsx` tracks `cases` and a `selectedBreakdownCaseId` for modal rendering, fetching the `vis-network`-ready contact-graph payload on demand when a case is expanded. `ClassTeacherDashboard.jsx` / `FacultyDashboard.jsx` manage `escalations`/`flags` arrays and fire the corresponding course/division-scoped GETs and the absence-flag POST.

### 2.10 What the end-to-end test suite actually proves

`test_e2e_scenario.py` runs exactly five scenarios: (1) seeding a timetable slot and two students, running the presence and graph builders, and asserting exactly one `ContactEdge` is created with 60 minutes' duration — proving the data pipeline correctly turns a schedule into a weighted edge; (2) a student filing a health report and receiving `201`, proving the report endpoint persists correctly and triggers server-side tracing; (3) the second student fetching their own alerts and finding risk data and symptoms present but **no source identity** — proving both that tracing correctly reached them and that the privacy boundary holds; (4) Health Admin fetching the contact graph and finding the second student correctly listed under `contacts.forward` — proving the BFS traversal and direction-filtering logic are correct against known ground truth; (5) Institute Admin fetching aggregates and finding a k-anonymized payload plus a new `audit_log` row — proving the privacy-and-accountability layer functions as a whole, not just component by component.

## 3. Known Limitations (Verified from Source)

- **Race condition in capacity allocation.** `capacity.occupied_beds += 1` has no pessimistic or optimistic row-level locking. Two concurrent allocation requests when exactly one bed remains can both read the same pre-update state, both confirm "there is room," and both increment — resulting in over-subscribed beds.
- **Hardcoded, non-configurable thresholds.** `HOP_CONFIDENCE_DECAY = 0.5` in `tracing_service.py` is hardcoded and does not consult `system_config`. `MATCH_MIN_SCORE = 0.20` in `disease_kb_service.py` is similarly hardcoded, blocking dynamic tuning of symptom-match sensitivity. `ROOM_TYPE_WEIGHT` defaults are statically defined at the top of `graph_builder.py` rather than read from configuration.
- **No transaction rollback trap in alert generation.** `alert_service.py`'s chained `Alert`-creation loop has no comprehensive `try/except` + `session.rollback()`. A failure partway through a batch (e.g., on record 3 of 5) leaves the first two alerts committed and the rest silently missing, with no surfaced error indicating the batch was incomplete.
- **The core structural limitation: timetable presence as a proxy for physical presence.** The entire contact graph assumes that being scheduled equals being physically present. It cannot capture unscheduled contact (corridors, dining halls, dorm common areas, study groups) and cannot detect when someone was actually absent from a session the timetable says they attended.
- **Naive symptom matching.** Exact lowercase token overlap with no stemming, synonym handling, or spell correction — "high temp" would not match a KB entry listing "fever," and simple typos break matching entirely.
- **Synchronous, in-memory processing throughout.** Presence generation, graph building, and tracing all run synchronously and in-memory per request/date — reasonable at pilot scale (one to two divisions, a few hundred users) but not the intended production shape.
- **No residential/unscheduled contact layer.** Consistent with Hartvigsen's (paper 14) finding that residential networks materially affect outbreak dynamics, CampusTrace currently only models academic (classroom/lab) contact.

## 4. Suggested Improvements (Prototype-Level, Not Yet Implemented)

- Add `SELECT ... FOR UPDATE` or an atomic conditional `UPDATE ... WHERE occupied_beds < capacity` to close the capacity race condition.
- Move `HOP_CONFIDENCE_DECAY`, `MATCH_MIN_SCORE`, and `ROOM_TYPE_WEIGHT` into `system_config` so Institute Admin can tune them without a code change.
- Wrap `alert_service.py`'s creation loop in a single transaction with explicit rollback on any failure, and surface a partial-failure error rather than silently under-notifying.
- Add lightweight stemming/synonym normalization (or a small curated synonym table) to `disease_kb_service.py` to reduce false-negative symptom matches.
- (Broader, architecture-level improvements — async job queues, indexing, and the Wi-Fi proximity proposal — are covered in the separate Improvements document, since they go beyond prototype-level fixes.)

## 5. Pros and Cons

**Pros**
- Fully implemented against its own documented contract — no gap between plan and reality.
- Zero new infrastructure required (no BLE/GPS/hardware) — deployable on data the institution already has.
- Transparent, auditable, entirely hand-written risk and traversal algorithms — nothing is a black box.
- Strong, structurally-enforced privacy model (RBAC + source concealment + k-anonymity + audit log).
- Deterministic, ground-truth-based end-to-end test coverage rather than only unit tests.
- Disease-agnostic configuration (Disease KB, tracing depth/direction as data, not code).

**Cons**
- Core contact graph accuracy is bounded by the timetable-presence assumption — cannot see unscheduled contact.
- Several meaningful hardcoded constants reduce runtime tunability.
- A real (if narrow) concurrency bug exists in capacity allocation.
- No transactional safety net in alert generation.
- Synchronous architecture will not hold up unmodified at full-university scale.
- Naive text-matching in the symptom suggester is fragile to real-world phrasing variance.

## 6. Twenty Questions an External Examiner Might Ask — Answered in Depth

**Q1. Walk me through what happens, end to end, the moment a student submits a health report.**
The `POST /student/health-report` handler persists a new `HealthRecord` row, then synchronously calls `tracing_service.trace_case()`, which pulls the index case's contact edges, filters them by direction/date relative to onset, and runs depth-bounded BFS/DFS to build the traced-contact set. That set is passed to `alert_service.generate_alerts()`, which deduplicates overlapping forward/backward hits, attaches symptoms from the Disease KB (or the reporter's custom text), and writes one `Alert` row per exposed user — all within the same request, before the `201` response is returned to the student.

**Q2. Why is `build_presence_for_date` idempotent, and why does that matter?**
It computes a set difference against existing `Presence` rows before inserting, so calling it twice for the same date never creates duplicates. This matters operationally because the presence-generation job is meant to be safely re-runnable — if it's re-triggered after a partial run, a crash, or a correction to the timetable, it won't corrupt the data by double-inserting.

**Q3. Why group by `(room_id, slot_id)` rather than just by room, or just by time?**
Grouping needs both dimensions together to correctly identify who was actually co-present in the same session — grouping by room alone would incorrectly merge two different classes held in the same room at different times of day; grouping by slot alone (without room) would incorrectly merge two sections of the same course period held in different rooms. `(room_id, slot_id)` is the minimal correct join key for "these people were physically together at the same time."

**Q4. Why `itertools.combinations` and not something else for edge generation?**
Because contact is symmetric and unordered — if A and B were both present, "A contacted B" and "B contacted A" are the same fact, not two. `combinations(group, 2)` generates each unordered pair exactly once per group, which is exactly the semantics an undirected weighted graph needs, and is both simple and provably correct for this purpose.

**Q5. What's the practical difference between forward and backward tracing in your implementation, in one sentence each?**
Backward tracing filters to `contact_date < onset_date` and looks for who the case might have caught the illness *from*; forward tracing filters to `contact_date >= onset_date` and looks for who the case might have exposed *afterward* — both run over the same underlying edge set, differing only in the date filter applied before traversal.

**Q6. Explain Noisy-OR aggregation in plain terms — why not just add up the scores from repeated contacts?**
Simply summing risk scores from multiple contacts between the same pair could easily exceed 1.0 (100%), which is meaningless as a probability. Noisy-OR treats each contact event as an independent chance of transmission and computes the probability that *at least one* of them succeeded: `1 − product(1 − score_i)`. This is mathematically bounded between 0 and 1 no matter how many contact events are combined, and correctly reflects that more independent exposures should increase — but never exceed certainty — the combined risk.

**Q7. Your `max_depth` defaults to 2. What does depth actually mean here, and why 2?**
Depth is the number of hops from the index case in the BFS/DFS traversal — depth 1 is direct contacts of the case, depth 2 is contacts-of-contacts, and so on. A default of 2 reflects a reasonable balance for a pilot: capturing likely secondary exposure (a contact who then exposed someone else) without the traced population ballooning to an unmanageably large fraction of the division at higher depths, and it's explicitly configurable per case via the retrace endpoint if Health Admin needs to widen it.

**Q8. Your test suite — walk me through the five scenarios and what each one actually proves.**
(1) Seeding a timetable slot and two students, then running the presence and graph builders, proves the *data pipeline* correctly turns a schedule into exactly one weighted contact edge with the right duration. (2) A student filing a health report and getting `201` proves the report endpoint correctly persists the record and triggers server-side tracing without erroring. (3) The second student fetching their own alerts and finding risk data present but the first student's identity absent proves both that tracing correctly reached them *and* that the privacy boundary holds. (4) Health Admin fetching the contact graph and finding the second student correctly listed as a forward contact proves the BFS traversal and direction-filtering logic work correctly against known ground truth. (5) Institute Admin fetching aggregates and finding both a k-anonymized payload and a new audit log entry proves the privacy-and-accountability layer functions together, not just individually.

**Q9. What happens if two health reports are filed for overlapping contact groups — does your system double-count or double-alert anyone?**
Within a single case's trace, deduplication is explicit: `alert_service.generate_alerts()` merges forward and backward results and keeps the higher score if a user appears in both. Across two *separate* cases naming an overlapping contact, however, each case's trace runs independently and would generate a separate `Alert` row per case — meaning a student could legitimately receive two distinct alerts if they were genuinely exposed via two different index cases, which is correct behavior, not a bug, since those are two genuinely separate exposure events.

**Q10. Why is `alert_service.py`'s lack of transaction wrapping a real problem, and what would actually go wrong?**
The alert-creation loop writes one `Alert` row per traced contact without a single enclosing transaction with rollback-on-failure. If a constraint violation or transient DB error occurs while writing the third of five alerts, the first two already-committed alerts stay in the database while the remaining two are silently never created — leaving some genuinely exposed contacts un-notified with no error surfaced to indicate the batch was incomplete. This is exactly the kind of latent bug invisible in normal demo conditions but likely to surface under real load or a real database hiccup.

**Q11. Explain the capacity allocation race condition in concrete terms — what sequence of events would actually break it?**
If two isolation-bed requests arrive concurrently when exactly one bed remains: both requests read `occupied_beds` from the same pre-update state (say, 9 of 10 occupied), both independently confirm "there is room," and both then execute `occupied_beds += 1` and create an `IsolationAllocation` row — resulting in 11 allocations against a 10-bed facility. The fix (not yet implemented) would be a database-level lock (`SELECT ... FOR UPDATE`) or an atomic conditional `UPDATE ... WHERE occupied_beds < capacity` to make the check-and-increment a single indivisible operation.

**Q12. Your symptom matcher uses simple word-overlap. What are its actual failure modes?**
Because it does exact lowercase token matching with no stemming, synonym handling, or spell-correction, it would fail to match "high temp" against a KB entry listing "fever" (no shared token despite meaning the same thing), and would fail on simple typos ("feaver"). It could also over-match on common but non-diagnostic words if a KB entry's symptom list isn't curated carefully, since the score is a simple overlap ratio rather than a weighted-term-importance measure. This is acceptable for a non-diagnostic triage aid but would need real hardening before being relied on for anything beyond suggestion.

**Q13. How many lines of code does this represent, and does that size feel appropriate for what's being built?**
Roughly 6,892 lines of backend Python and 1,600 lines of React, plus a 259-line schema — around 8,750 lines total. This is a reasonable size for a system implementing five hand-written core algorithms, five distinct role-scoped API surfaces, and five matching dashboards, without being bloated; the roughly 4:1 backend-to-frontend split reflects that the project's substance is genuinely in the tracing/risk logic, with the frontend deliberately kept simple per the stated tech-stack rationale.

**Q14. If I gave you a real dataset of 5,000 students right now, what would break first?**
Almost certainly the synchronous, in-memory grouping step in `graph_builder.py`, which loads all of a day's `Presence` rows into memory and groups them with plain Python dictionaries — at 5,000 students across many rooms/slots this is still likely tractable for a single division, but scaling to a full multi-thousand-student institution across many divisions would start to strain per-request memory and latency, especially since tracing currently also runs synchronously inline with the API request. This is exactly the scaling profile the Improvements document addresses with async job queues and possible pre-aggregation.

**Q15. Does the frontend do any client-side validation, or is everything trusted to the backend?**
Based on the confirmed component/state structure, form-driven POSTs (health report, absence flag, divisions/rooms/courses creation) go through standard React form state before submission, but the authoritative validation — required fields, role authorization, data shape — is enforced server-side per the API contract's stated error conventions (`400` for bad input, `403` for wrong role), which is the correct security posture: client-side validation is a UX convenience, never a substitute for server-side enforcement, and nothing in the reviewed code suggests server-side checks are skipped.

**Q16. How does the Health Admin dashboard actually render the contact graph — what library, and how is risk shown visually?**
It uses `vis-network` for the graph rendering. The source case is shown as a gold node, and traced contacts are colored by risk tier — red for high risk, orange for medium, green for low — with edge labels showing contact duration, giving Health Admin an immediately scannable visual read of an outbreak's shape (a tight red cluster vs. a sparse scatter of green edges) without needing to read a data table.

**Q17. What's the actual difference between your `GET /health-admin/contact-graph/<id>` and `POST /health-admin/contact-graph/<id>/retrace`?**
The GET returns the currently stored/most recent trace result for that case in the same node/edge JSON shape. The POST re-runs tracing with caller-supplied parameters (`direction`, `max_depth`) that override the system defaults for that specific case — this is the mechanism that operationalizes the literature's "tracing direction should be context-dependent" finding, letting Health Admin manually widen or redirect a trace if the default parameters aren't producing a useful picture for a particular outbreak.

**Q18. What guarantees does the system give that a student can't see another student's data, even by tampering with the request?**
Every student-scoped route filters by the user ID embedded in the signed JWT, not by any ID supplied in the URL or body — so even if a student manually edited a request to reference another student's numeric ID, the backend would still only query and return the authenticated caller's own rows, because the query itself is constructed from the token's identity, not from client input. This is the same pattern (`role_required` + token-derived scoping) applied consistently across faculty-course-assignment checks and division-level scoping for Class Teacher routes.

**Q19. Is there any part of the prototype that is more "for show" (demo-only) than production-ready?**
Yes, and this is worth being upfront about: the synchronous tracing design and the CLI-invoked sequential presence-generation script are both reasonable for a pilot/demo but are explicitly *not* the intended production shape — the Methodology's own Phase 5 names asynchronous background tracing (Celery/Redis) as necessary "for production-scale institution deployment," meaning the current synchronous design is a deliberate, acknowledged simplification for the pilot phase, not a claim that it's how a real multi-thousand-user deployment should run.

**Q20. If an examiner picks one seeded test case at random and asks you to trace it live, could you do it, and what would you show them?**
Yes — this is exactly what the seed script and `test_e2e_scenario.py` are built to support (the README specifically calls out Case #5 as a good demo starting point). The demo would: log in as Health Admin, open the Health Cases Tracker, select the case, choose a tracing direction and depth, click Trace Case, and show the resulting `vis-network` graph with the gold source node and color-coded contacts; then switch to the affected student's account to show the corresponding alert with risk data but no source identity; then open Institute Admin to show the same event reflected in a k-anonymized aggregate and a new audit log row — walking the exact same chain the automated e2e test verifies programmatically, live.
