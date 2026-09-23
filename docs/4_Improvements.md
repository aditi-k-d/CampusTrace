# CampusTrace — Improvements & Scalability Roadmap

This document covers two things: (A) general improvements to take CampusTrace from a verified pilot to a scalable, university-wide system, and (B) a detailed feasibility analysis of the specific idea raised — using **Wi-Fi** (association/proximity to access points) instead of, or alongside, BLE, to trace infected individuals and their contacts, given that most phones today have BLE off by default while campus Wi-Fi is near-universally connected.

---

## Part A — General Improvements for University-Scale Deployment

### A.1 Concurrency and correctness hardening

- **Fix the capacity race condition** identified in the Prototype Analysis: replace the read-then-increment pattern with an atomic conditional update (`UPDATE capacity SET occupied_beds = occupied_beds + 1 WHERE id = ? AND occupied_beds < total_beds`) or a `SELECT ... FOR UPDATE` row lock, so concurrent allocation requests cannot both succeed against the same last bed.
- **Wrap `alert_service.py`'s alert-creation loop in a single transaction** with explicit rollback on any failure, and surface a clear partial-failure error to the caller (and to the audit log) rather than silently under-notifying exposed contacts.
- **Move hardcoded thresholds into `system_config`**: `HOP_CONFIDENCE_DECAY`, `MATCH_MIN_SCORE`, and `ROOM_TYPE_WEIGHT` should all become institution-tunable configuration rather than code constants, so an institution can calibrate them to its own population and risk tolerance without a redeployment.

### A.2 Performance and architecture at scale

- **Move tracing and presence/graph generation to an asynchronous job queue** (Celery/Redis, as the project's own Methodology already names for Phase 5). At full-university scale (multiple divisions, thousands of students, potentially hundreds of health reports per day during an active outbreak), synchronous in-request tracing risks slow API responses and resource contention; an async worker pool decouples "report filed" from "tracing completed," with the student/faculty seeing an immediate acknowledgment and the alert arriving moments later.
- **Pre-aggregate or incrementally maintain the contact graph** rather than rebuilding groupings from scratch per date/case at query time — e.g., maintain rolling per-user adjacency lists updated incrementally as presence is generated, rather than re-deriving them per trace request.
- **Database indexing review** for the columns actually hit hardest at scale: `contact_edges(user_a_id, contact_date)`, `contact_edges(user_b_id, contact_date)`, `presence(user_id, presence_date)`, and `alerts(user_id, acknowledged)` — none of these are confirmed indexed beyond the schema's stated unique constraints, and query latency on these tables will dominate as row counts grow into the millions.
- **Horizontal read scaling for dashboards**: k-anonymized aggregate dashboard queries (Institute Admin) are read-heavy and can tolerate slightly stale data — a read replica or a periodically refreshed materialized aggregate table would keep dashboard load off the primary tracing path.

### A.3 Organizational scaling

- **More divisions, more roles, more concurrent report volume.** The schema already supports this cleanly (`division_id` as a foreign key throughout, per the Project Overview's own design intent), but operational scaling means the Health Admin role likely needs to become a *team* with sub-scoping (e.g., "Health Admin, Division X") rather than a single account seeing every division at once, once the institution is large enough that one person reviewing every case becomes a bottleneck.
- **Delegated / tiered case review** — a triage layer where lower-risk cases can be auto-classified and only high-risk or ambiguous cases require Health Admin manual confirmation, reducing per-case load as volume grows.

### A.4 Data quality and coverage improvements

- **Attendance verification, not just scheduled presence.** Cross-reference `Presence` rows against any independently available attendance signal (e.g., faculty-confirmed attendance, an existing attendance system) so absent-but-scheduled individuals are excluded from contact edges rather than assumed present.
- **A residential/dormitory contact layer**, directly motivated by Hartvigsen's (Literature Review, paper 14) empirical finding that residence-hall network structure materially changes outbreak dynamics on a real campus. This could reuse the exact same `Presence`/`ContactEdge` model, keyed to room-assignment data instead of timetable data.
- **This is exactly where the Wi-Fi proximity idea fits** — as a way to add a *verification and coverage* signal for both scheduled and unscheduled contact, without reintroducing the adoption-dependency and privacy problems of BLE apps. Detailed below.

### A.5 Symptom-matching quality

- Add basic stemming (e.g., "fevers"/"feverish" → "fever") and a small curated synonym table (e.g., "high temp" → "fever") to `disease_kb_service.py`, meaningfully reducing false-negative matches without requiring a heavier NLP dependency, consistent with the project's stated avoidance of black-box ML.

### A.6 Observability

- Structured logging and basic metrics (trace latency, alert-generation success rate, capacity-allocation contention) would give an operator early warning of exactly the kind of failure modes named in Part A.1 — race conditions and silent partial failures are much easier to catch with monitoring than to discover from user complaints.

---

## Part B — Can Wi-Fi Be Used Instead of BLE? Full Feasibility Analysis

### B.1 The premise, and why it's a genuinely good question

The concern raised is accurate and well-supported by real device behavior: **BLE requires a user to keep Bluetooth actively on and an app running/backgrounded to scan**, and in practice a large fraction of students leave Bluetooth off unless actively using it (headphones, etc.) — creating exactly the adoption-gap coverage problem the Literature Review documents mathematically (Zhang & Britton, papers 9/10; Benthall et al., paper 12). **Wi-Fi, by contrast, is close to universally connected on a campus** — students keep Wi-Fi on essentially all the time to use the internet, and connecting to the campus network is often a precondition for using institutional services at all. If proximity/presence could be inferred from Wi-Fi behavior instead of requiring active BLE scanning, the adoption ceiling that limits BLE-based approaches would largely disappear.

**Short answer: yes, this can be implemented, and it would meaningfully improve on both BLE-based approaches and CampusTrace's own current timetable-only model — but it is a complement to the existing timetable-derived graph, not a wholesale replacement, and it comes with real infrastructure and privacy tradeoffs that need to be designed for explicitly.**

### B.2 How Wi-Fi-based proximity inference would actually work

There are two meaningfully different techniques, and it's important to distinguish them because they have very different feasibility profiles:

**B.2.1 Access-point (AP) association inference (recommended, higher feasibility)**

Modern campus Wi-Fi is deployed as many access points, each covering a physical zone (a specific building floor, sometimes down to a specific room or lecture hall in a dense deployment). Every device connected to the campus Wi-Fi network is, at the network infrastructure level, associated with a specific AP at any given time, and this association is already logged by the Wi-Fi controller/RADIUS server for basic network administration and security purposes.

- **What it captures:** which AP (i.e., roughly which physical zone) a device is connected to, and for how long — a coarse but real proximity signal. Two devices connected to the *same* AP for an overlapping time window were very likely physically near each other (in the same room or adjacent zone that AP serves).
- **How it would integrate with CampusTrace:** a new ingestion service would periodically (e.g., every few minutes) pull AP-association logs from the Wi-Fi controller, map each AP to the room(s) it covers (a one-time mapping configuration, similar to how `rooms` already exist in the schema), and generate `Presence`-equivalent rows keyed by (user, AP-derived room, time window) — feeding directly into the *existing* `graph_builder.py` pairwise-combination logic, since the data shape is compatible with what the system already consumes.
- **Data source:** this data already exists in essentially every enterprise/campus Wi-Fi deployment (Cisco, Aruba, Ubiquiti, etc. controllers all log AP associations) — no new hardware is needed, only an integration to read logs the network infrastructure already produces for its own operational purposes.

**B.2.2 Fine-grained RSSI/triangulation-based proximity (lower feasibility, not recommended as a first step)**

A more precise approach uses signal-strength (RSSI) readings from multiple nearby APs to triangulate a device's position more precisely than "which AP it's connected to," potentially distinguishing two devices in the same room from two devices in adjacent rooms served by the same AP. This requires either specialized indoor-positioning infrastructure (rarely present on a typical campus Wi-Fi deployment) or app-side RSSI scanning (which reintroduces an adoption-dependency problem similar to BLE, since it requires an installed, actively-running app). **This tier is not recommended for an initial implementation** — it adds significant infrastructure cost and complexity for a precision gain that AP-association-level granularity mostly doesn't need, given that CampusTrace's risk model already operates at the "room" level of granularity, not sub-room precision.

### B.3 Why AP-association is the right level of granularity for this system specifically

This is an important, non-obvious point: CampusTrace's existing risk model (`room_type_weight`, duration, recency) already operates at **room-level** granularity, not exact-meter positioning. AP-association data is naturally room-or-zone-level in a well-planned deployment (one AP typically serves one or a few nearby rooms). This means Wi-Fi AP data is not just feasible but is actually a **precision-matched** data source for the system as it already exists — no risk-formula redesign is needed, only a new `Presence`-generating data source that feeds the exact same downstream pipeline (`graph_builder.py` onward) the timetable data feeds today.

### B.4 Concrete implementation plan

1. **AP-to-room mapping.** A one-time administrative task (extending the existing `rooms` table with an `ap_ids` or a new `wifi_access_points` mapping table linking each AP's identifier to the room(s) it serves) — this is genuinely new setup work but is a static configuration task, not an ongoing burden.
2. **Association-log ingestion service.** A new scheduled job (parallel in structure to `presence_builder.py`) that queries the Wi-Fi controller's API or reads its association logs on a fixed interval, extracts (device/user identifier, AP, start-time, end-time) tuples, and maps them to (user, room, time-window) records.
3. **Device-to-user identity resolution.** Campus Wi-Fi authentication (WPA2-Enterprise / 802.1X, the standard for institutional Wi-Fi) already ties a connected device to a logged-in institutional identity for authentication purposes — this is the critical enabler that makes user-identity resolution straightforward and requires no new consent flow beyond what logging into campus Wi-Fi already involves.
4. **Feed into the existing `Presence`/`ContactEdge` pipeline.** Rather than building a parallel system, Wi-Fi-derived presence records are inserted using the *same* `Presence` model and consumed by the *same* `graph_builder.py` combination logic already in place — timetable-derived and Wi-Fi-derived presence become two **complementary sources feeding one unified contact graph**, distinguished by a `source` field (`timetable` vs `wifi`) so each edge's provenance stays auditable and either source can be disabled or reweighted independently.
5. **Reconciliation logic.** Where both a timetable-predicted presence and a Wi-Fi-observed presence exist for the same user/room/time, the system gains a genuine **verification signal** — timetable said they should be there *and* Wi-Fi confirms they were, which could raise confidence/weight on that edge. Where Wi-Fi shows presence with **no** matching timetable entry (unscheduled contact — a study group, a corridor conversation, a library co-location), a *new class of contact edge* becomes possible that the current system cannot see at all today.
6. **Retention and minimization policy.** Raw AP-association logs should be retained only as long as needed to generate the derived `Presence`/`ContactEdge` records (a short rolling window, e.g., 14–21 days, matching the system's own tracing depth/recency-decay horizon), then discarded — the system should store the *derived* graph data it already has a privacy model for, not an indefinitely-retained raw location log.

### B.5 Why this is better than the current (timetable-only) prototype

- **Closes the single biggest named limitation.** The Prototype Analysis and Topic Analysis both identify the timetable-presence assumption — "scheduled equals present" — as the system's core weakness. Wi-Fi presence directly verifies or corrects that assumption rather than trusting it blindly.
- **Captures unscheduled contact for the first time.** Dorm common areas, libraries, dining halls, hallway conversations, and study groups — exactly the kind of contact Hartvigsen's residential-network research (Literature Review, paper 14) shows matters for real outbreak dynamics — become visible, closing that specific, previously-acknowledged gap.
- **No new hardware, no new app, no adoption ceiling.** Unlike BLE, this uses network infrastructure the institution already operates and that students already use continuously by habit (to get internet access), so coverage is not capped by opt-in behavior the way BLE-app coverage would be.
- **Precision-matched to the existing risk model** rather than requiring a redesign, as explained in B.3 — this is a genuinely low-friction extension of the current architecture, not a rebuild.

### B.6 Why this is better than the *original* BLE-style prototype pattern most contact-tracing apps use

- **No battery drain from continuous BLE scanning**, and no dependency on users remembering to enable and keep Bluetooth on — Wi-Fi association is a byproduct of devices already being connected for internet access, requiring zero additional user behavior.
- **No separate app install required.** BLE-based apps (TraceTogether-style) need a dedicated app running to perform proximity scanning; Wi-Fi AP association is captured entirely at the network-infrastructure level, invisible to and requiring nothing from the end-user device beyond being connected to campus Wi-Fi as they already are.
- **More robust identity binding.** WPA2-Enterprise Wi-Fi authentication ties a connection directly to an institutional identity; BLE proximity apps typically rely on rotating anonymous identifiers exchanged between devices, which is good for cross-institutional privacy but makes matching a "contact" back to an actual institutional user harder and requires the app itself to have been running and exchanging beacons at the right moment.

### B.7 Honest tradeoffs and risks this introduces — not glossed over

- **Coarser granularity than BLE in one specific sense.** BLE proximity (when it works) can in principle detect very close physical proximity (within a few meters) regardless of room boundaries; AP-association only tells you "same AP zone," which could occasionally span more than one room in a dense deployment, or fail to distinguish two adjacent seats from two ends of a large lecture hall served by the same AP. This is a real precision tradeoff, not a strict improvement in every dimension — it's a *coverage* improvement traded partly against *fine-grained* precision, which for this system's room-level risk model is judged to be the right trade (per B.3), but should be stated honestly rather than oversold.
- **New infrastructure dependency.** This requires integration access to the Wi-Fi controller/RADIUS logs — a genuine new dependency on IT infrastructure cooperation that the current timetable-only system doesn't need. This is not "zero new infrastructure" in the way the current prototype is; it is *zero new hardware* but *does* require a data-integration project with the network team.
- **Privacy surface increases and must be deliberately re-scoped.** Wi-Fi association data is, in raw form, a genuine indoor-location log — a materially larger privacy footprint than timetable data (which only implies "scheduled to be somewhere," not "observed to actually be there in real time"). This must be met with equally deliberate scope-narrowing: strict retention limits (B.4.6), storing only derived Presence/ContactEdge records rather than raw logs beyond the minimum needed window, and treating this data source with at least the same RBAC/audit rigor already applied to the rest of the system — arguably more, since it is more sensitive than the current data.
- **Off-campus or non-connected periods remain invisible**, same as today — a student who is present in a room but has Wi-Fi disabled, or who is off the institutional network on cellular data, would not generate a Wi-Fi-derived presence record for that period. This narrows, but does not eliminate, the class of contact the system can't see (unlike a hypothetical universal sensor, no proxy-data approach achieves perfect coverage).
- **Requires clear institutional policy and consent framing**, since this extends what the Wi-Fi network's operational logs are used for beyond pure network administration — an institution would need to update its Wi-Fi usage policy/acceptable-use agreement to disclose this secondary use, which is a governance step, not just an engineering one.

### B.8 Recommended rollout approach

Rather than replacing the timetable-derived graph, the recommended path is **additive and staged**:

1. Pilot AP-association ingestion in parallel with the existing timetable pipeline for one division, comparing Wi-Fi-derived presence against timetable-derived presence to validate the reconciliation logic (B.4.5) on real data before trusting it operationally.
2. Use the reconciliation signal first purely as a **confidence booster / discrepancy flag** for Health Admin (e.g., "timetable says present, Wi-Fi disagrees — flag for review") rather than immediately feeding unscheduled-contact edges into automated alerting, to build institutional trust in the new source before it directly drives notifications.
3. Once validated, enable Wi-Fi-only (unscheduled) contact edges as a distinct, clearly-labeled edge type in the graph and dashboards, so Health Admin can always see whether a given traced contact came from a scheduled class or an unscheduled Wi-Fi co-location — preserving the same transparency and auditability principle the rest of the system is built on.

### B.9 Verdict

Yes — Wi-Fi AP-association-based proximity inference is technically feasible, requires no new hardware, closes the two most significant gaps in the current prototype (the timetable-presence assumption and the missing unscheduled/residential contact layer), and is a strictly better fit for real device behavior on campus than a BLE-based approach given that Wi-Fi is what students actually keep on. It should be implemented as an **additive second data source feeding the existing `Presence`/`ContactEdge` pipeline**, not a replacement for the timetable-derived graph — the two sources are complementary (one gives clean, high-confidence *scheduled* contact; the other gives broader, somewhat coarser *actual observed* contact including the unscheduled cases the system currently misses entirely) — provided the retention, consent, and infrastructure-dependency tradeoffs in B.7 are addressed deliberately as part of the rollout rather than treated as afterthoughts.
