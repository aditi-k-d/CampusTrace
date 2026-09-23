# CampusTrace — Topic Analysis

## 1. Problem Statement

Institutional outbreaks of infectious disease — a flu wave through a dormitory, chickenpox through a batch, norovirus through a shared mess hall, or the next campus-scale respiratory illness — are currently handled either manually (informal word-of-mouth, a health center noting a diagnosis with no systematic follow-up) or, at best, with tools built for a completely different scale and context: national contact-tracing apps designed hastily during COVID-19 for entire populations (Aarogya Setu, TraceTogether, and their international equivalents). Both approaches share structural weaknesses when applied to a bounded institution like a college:

1. **Adoption-capped coverage.** National apps rely on voluntary Bluetooth/GPS opt-in, so their effectiveness is capped by adoption rate, not by the population actually at risk. The literature (Zhang & Britton; Benthall et al.) confirms this mathematically — digital tracing effectiveness is directly bounded by the app-using fraction.
2. **Binary, ungraded output.** They produce "you were near a case" / "you weren't" alerts with no sense of how risky the actual contact was — a 5-minute corridor pass-by is treated identically to a 90-minute shared lab session.
3. **Single-disease, emergency-only design.** Built and deployed in crisis, then abandoned once the crisis passes, with no institutional memory or reusable infrastructure for the next outbreak (chickenpox, mumps, flu, or whatever comes next).
4. **Disconnected from institutional response capacity.** They notify individuals but do nothing to help an administrator actually manage isolation beds, prioritize testing, or spot an emerging cluster before it grows.
5. **No institutional role model.** A "citizen" is the only role a national app understands. A campus has meaningfully different stakeholders — student, course instructor, division-level teacher, health authority, institute administrator — each legitimately needing a different, role-appropriate slice of the same underlying information.

There is, therefore, a genuine and currently unmet need for a **disease-agnostic, privacy-preserving contact-tracing system purpose-built for closed institutional environments**, that produces graded, actionable risk signals instead of binary alerts, and that directly supports administrative infection-control decision-making rather than stopping at individual notification.

## 2. Need for the Topic — Why This Matters Now

- **Residential and academic institutions are structurally high-transmission environments.** Shared classrooms, labs, hostels, mess halls, and transport create dense, repeated contact patterns — Hartvigsen's SUNY Geneseo study (paper 14 in the Literature Review) empirically shows real college contact networks have materially different (and in some ways riskier — long right-skewed degree distributions up to hundreds of contacts) structure than random mixing.
- **The COVID-19 pandemic proved the demand exists, but also proved most solutions were the wrong shape for anything but a nation-scale emergency.** Once the emergency passed, adoption collapsed and most apps were retired — the underlying *need* for fast, low-friction exposure notification for ordinary institutional outbreaks (which happen constantly, pandemic or not) never went away, but the infrastructure to meet it did.
- **Institutions already collect the data needed — it's just not being used this way.** Timetables, enrollment records, and room bookings exist for purely administrative reasons; CampusTrace's insight is that this same data, already legitimately held, is sufficient to build an accurate proximity graph without any new hardware or surveillance infrastructure.
- **Privacy expectations have risen, not fallen, since 2020.** A solution proposed today has to satisfy tighter privacy expectations than a 2020 emergency app was held to — which is why CampusTrace treats privacy (RBAC, source-identity concealment, k-anonymity, audit logging) as a first-class architectural concern rather than an afterthought.

## 3. Why This Solution Is the Right Approach (vs. Alternatives)

| Alternative approach | Why it falls short here | CampusTrace's answer |
|---|---|---|
| BLE/Bluetooth proximity apps (TraceTogether-style) | Needs an app installed and Bluetooth kept on; adoption gap directly caps coverage; drains battery; many phones have BLE turned off by default habitually today | No app-side sensing required at all; the contact graph is derived server-side from institutional records that already exist |
| GPS-based tracking | Poor indoor accuracy (can't distinguish adjacent rooms or floors); heavy privacy concerns from continuous location logging; battery-intensive | No location tracking whatsoever; presence is inferred from timetable + room booking, already accurate to the exact room |
| Manual interview-based tracing | Slow — multi-day median delay per the Li et al. and Zhang & Britton findings in the Literature Review — relies on fallible memory, doesn't scale with caseload | Automated, synchronous trace the moment a report is filed; no interviewer, no delay, no memory-dependent recall |
| National-scale apps repurposed for a campus | Built for millions, not hundreds; no institutional-role awareness (no "class teacher" or "course faculty" concept); binary alerts only | Purpose-built 5-tier academic role hierarchy; graded, weighted risk scoring instead of binary |
| Doing nothing / spreadsheet-based manual tracking | No graph reasoning, no risk weighting, no privacy structure, entirely manual and error-prone at any real scale | Structured contact graph, algorithmic risk scoring, automated alerts, and audited role-based access control |

## 4. Where Existing / Comparable Projects Fall Short

- **Binary rather than graded output.** Most existing tools (and much of the modelling literature) treat "contact" as a yes/no fact, discarding information that clearly matters for risk — duration, recency, and setting.
- **No institutional role model.** National apps have essentially one role: "citizen." Off-the-shelf tools don't model the layered academic hierarchy a campus actually has.
- **Adoption-dependent coverage.** As the Literature Review shows (Zhang & Britton; Li et al.), digital tracing built around opt-in apps has a hard adoption ceiling baked into its design — coverage can never exceed adoption rate no matter how good the underlying algorithm is.
- **No connection to response capacity.** Being told "you were exposed" is not the same as an institution being able to *do* something about it — allocate isolation space, prioritize testing, spot an emerging cluster. Most tracing tools stop at notification and leave the operational response entirely manual.
- **Opaque or non-existent risk methodology.** Many commercial and government tools (including the graph-database deployment in Mao et al., paper 15) do not publish or explain how their risk/priority scores are actually computed, making them difficult to audit, trust, or defend to a review board.

## 5. Where CampusTrace Specifically Shines

- **Zero new infrastructure required.** No BLE beacons, no GPS hardware, no app-adoption campaign — it runs entirely on data the institution's existing timetable/enrollment system already holds.
- **Graded, explainable risk.** Every alert carries a transparent, auditable risk score (duration × recency decay × room-type weight, Noisy-OR aggregated across multiple contacts) rather than a black-box or binary signal.
- **A privacy architecture enforced in code, not policy.** Role-based access control read from a signed JWT, source-identity concealment for alerted students, server-side k-anonymity suppression on all aggregate views, and a full audit log of fine-grained access — four independent, structural privacy layers.
- **Disease-agnostic by design.** The Disease Knowledge Base, tracing depth/direction, and risk thresholds are all configurable data, not hardcoded to COVID-19 or any single pathogen — the same system handles chickenpox, flu, or the next unknown illness without a rebuild.
- **Operationally complete, not just a notifier.** Isolation-bed capacity tracking with priority-queue-driven allocation and k-anonymized institution-wide dashboards close the loop from "detect exposure" to "actually manage the outbreak," which most comparable systems in the literature (and in practice) stop short of.

## 6. Relevance to Sustainable Development Goals (SDGs)

| SDG | How CampusTrace contributes |
|---|---|
| **SDG 3 — Good Health and Well-Being** | The core contribution: faster, more accurate exposure detection reduces onward transmission within the institution, directly supporting target 3.3 (combating communicable diseases) and 3.d (strengthening capacity for early warning and health-risk management) at institutional scale. |
| **SDG 4 — Quality Education** | By containing outbreaks faster and more precisely (individual/small-group isolation rather than blanket closures), CampusTrace helps minimize disruption to continuous, in-person instruction — a real tradeoff institutions faced during COVID-19, where blunt, whole-campus shutdowns were often the only available tool. |
| **SDG 9 — Industry, Innovation and Infrastructure** | Demonstrates that meaningful public-health infrastructure can be built from **existing** institutional data systems rather than requiring new hardware deployment (BLE beacons, GPS infrastructure) — a resource-efficient innovation model appropriate for institutions with limited budgets, including in lower-resource settings. |
| **SDG 10 — Reduced Inequalities** | Because coverage does not depend on owning a particular phone, keeping Bluetooth on, or opting into an app, the system does not systematically under-cover students with older devices, privacy-conscious students who decline to install tracking apps, or students who simply forget to — closing exactly the adoption-gap inequities BLE/GPS apps create. |
| **SDG 11 — Sustainable Cities and Communities** | A college campus is a dense, semi-closed micro-community; CampusTrace's model of deriving a proximity graph from shared institutional infrastructure (rooms, schedules) is a template that generalizes to other bounded communities — corporate campuses, hospitals, residential complexes — that similarly want resilient health-response infrastructure without new surveillance hardware. |
| **SDG 16 — Peace, Justice and Strong Institutions** | The privacy-by-architecture design (RBAC, audit logging, k-anonymity, source-identity concealment) models accountable, transparent institutional data governance — every fine-grained access is logged and reviewable, directly supporting target 16.10 (public access to information while protecting fundamental freedoms). |

---

## 7. Twenty Questions an External Examiner Might Ask — Answered in Depth

**Q1. Why did you choose this topic over something more conventional?**
Most conventional capstone topics (a generic CRUD app, a recommendation engine, a chatbot) don't require genuinely combining data-structures theory with a real institutional need. Contact tracing does: it needs a real graph (not a metaphorical one), real traversal algorithms with a real reason to be depth-bounded and bidirectional, a real priority queue with a real resource-scarcity problem behind it (isolation beds), and a real privacy-architecture problem, all serving an actual, currently-unmet institutional need. It let the team demonstrate DSA fundamentals (graphs, BFS/DFS, Union-Find, heaps) in a context where those choices are *load-bearing*, not decorative.

**Q2. What exactly is novel here — isn't contact tracing a solved problem after COVID-19?**
Contact tracing *technology* got a lot of attention during COVID-19, but almost entirely in the shape of national, single-disease, BLE/GPS-opt-in apps — a shape that is a poor fit for a bounded, structured institution and that mostly disappeared once the emergency ended. What's novel here is the combination: deriving the contact graph entirely from institutional records rather than device sensing, making risk graded and disease-agnostic rather than binary and COVID-specific, and building a five-tier role hierarchy with response-capacity tooling rather than a bare notifier. No single piece is individually unprecedented — the novelty is in fitting them together for this specific, underserved context.

**Q3. What's the actual benefit to the institution deploying this, in concrete terms?**
Faster outbreak containment with far less disruption: instead of a blanket "close the whole division for two weeks" response born of uncertainty about who's actually at risk, an institution gets a ranked, risk-scored list of specific individuals to check on, informed decisions about isolation capacity, and a k-anonymized view of where an outbreak is concentrated — enabling targeted rather than blunt interventions.

**Q4. What's the benefit to an individual student?**
A student gets faster, more relevant exposure information (risk level, symptoms, recommended action) without needing to install a separate app, keep Bluetooth on, or worry that their exact contacts are disclosed to anyone — including the person who exposed them. They also get a self-assessment triage tool available anytime, not only tied to formally reporting an illness.

**Q5. How does this relate to the Sustainable Development Goals?**
Primarily SDG 3 (Good Health and Well-Being) via faster communicable-disease containment, but meaningfully also SDG 4 (Quality Education, by minimizing academic disruption from outbreaks), SDG 10 (Reduced Inequalities, by not depending on device ownership or app adoption), and SDG 16 (Strong Institutions, via the audited, transparent privacy architecture). See the SDG table above for the full mapping.

**Q6. Isn't deriving contact from timetable presence a huge assumption? What if someone skips class or sits somewhere unexpected?**
Yes — this is the single most important limitation of the current prototype, and it's named explicitly rather than glossed over (see Prototype Analysis, Q5 and Q15). The system currently assumes scheduled presence equals actual physical presence. It is a reasonable, privacy-friendly, zero-new-infrastructure *starting point*, not a claim of perfect ground truth — which is exactly why the Improvements document proposes a lightweight Wi-Fi association layer as a complementary, non-invasive way to verify and refine this assumption rather than replace it.

**Q7. Why not just use existing commercial contact-tracing software?**
Commercial and national-government solutions are built for a different scale (millions, not hundreds), a different context (single emergency disease, not disease-agnostic ongoing use), and typically ship as opaque, closed systems whose risk methodology an institution cannot inspect, audit, or adapt to its own academic role structure. A purpose-built system can be tailored exactly to this institution's actual division/batch/role model, and its logic is fully documented and explainable rather than a licensed black box.

**Q8. What happens to privacy if the Health Admin account itself is compromised?**
This is a real residual risk in any system granting fine-grained access to *someone* — CampusTrace's answer is defense-in-depth rather than a claim of immunity: every Health Admin action against fine-grained data (viewing a contact graph, re-triggering a trace) writes an audit log row, so a compromised or misused account is independently detectable after the fact even if not prevented in real time. This is consistent with how real institutional systems handle privileged access — audit, not just prevention.

**Q9. Your system claims to be "disease-agnostic" — how, concretely?**
The Disease Knowledge Base is editable data, not code — Health Admin can add or edit diseases, their symptoms, preventive measures, and incubation periods without a system rebuild. Tracing depth, tracing direction, and risk thresholds all live in `system_config`, not hardcoded constants tied to any one disease's known parameters. The same pipeline that traced a seeded chickenpox-style test case would trace a norovirus or influenza case identically, with only the Disease Knowledge Base content differing.

**Q10. Why does risk decay exponentially with time rather than linearly or with a hard cutoff?**
A hard cutoff (e.g., "contacts older than 7 days don't count") creates an artificial cliff where a 6-day-old contact is treated as fully relevant and a 8-day-old one as fully irrelevant, which doesn't match how transmission risk actually behaves. Exponential decay gives a smooth, monotonic reduction in relevance over time — a standard functional form in epidemiological exposure modelling — without an arbitrary threshold.

**Q11. Could this system be misused for surveillance beyond its stated health purpose?**
Any system that can construct a contact graph carries this theoretical risk, and CampusTrace's design deliberately narrows it: the data used (timetable/enrollment/room presence) is already collected for purely administrative reasons and is not expanded for this purpose; access to fine-grained contact data is restricted to the Health Admin role and audited; and aggregate views available to Institute Admin are k-anonymized specifically so that even the most senior administrative role cannot use the dashboards to identify a specific individual's movements. This is a meaningfully narrower footprint than the vehicle/public-place/government-data model in Mao et al. (paper 15 in the Literature Review), which the project deliberately did not follow.

**Q12. How is this different from just tracking attendance?**
Attendance tracking answers "who was supposed to be where." CampusTrace goes further: it converts that presence data into a weighted relational graph, runs depth-bounded traversal to find who is connected to a reported case within a configurable number of hops, and scores each connection by a transmission-risk formula — attendance is the input, not the output.

**Q13. What makes the risk scoring "algorithmic" rather than just a lookup table or a set of if-else rules?**
It genuinely uses graph algorithms end to end, not just a scoring rule applied to a static list: BFS/DFS traversal to discover the traced population in the first place (a lookup table can't do multi-hop discovery), Union-Find to detect connected clusters among high-risk contacts, and a priority queue/heap to rank contacts for scarce isolation resources — the risk formula itself is comparatively simple arithmetic, but it operates over structures and traversals that are genuinely algorithmic, hand-implemented specifically so the logic is fully explainable rather than hidden behind a library call.

**Q14. If the goal is privacy, why build a system that creates a detailed contact graph at all — isn't that itself a privacy risk?**
Any effective contact-tracing system, digital or manual, necessarily involves knowing who was near whom — that's not unique to this design, and refusing to build the graph at all would mean giving up on tracing altogether. The relevant privacy question isn't "does a graph exist" but "who can see it, in what form, and is that access accountable" — which is exactly what the RBAC, identity-concealment, k-anonymity, and audit-log layers are built to answer. The graph exists only where it needs to (the tracing service and the Health Admin's audited view of it); it is never exposed to a student, faculty member, or even Institute Admin in raw form.

**Q15. Why five roles specifically — why not fewer or more?**
Five roles map onto real, distinct decision-making levels that already exist in a college's structure: a student (own data only), course faculty (own course/batch), class teacher (own division across courses — meaningfully different once a second division exists), health admin (operational, fine-grained, audited authority), and institute admin (policy-level, k-anonymized-only authority). Collapsing roles (e.g., merging Health Admin and Institute Admin) would violate the principle that policy-setting and case-by-case operational access should be separated — the same reason many real institutions separate a data-protection officer from operational staff.

**Q16. What's the single strongest argument against building this at all — the best case for the "con" side?**
The strongest counterargument is that any system reasoning over students' health and location-in-time data, however well-intentioned, creates a new institutional dataset that didn't functionally exist as a queryable graph before, and that dataset itself becomes a target — for a data breach, for policy mission-creep (e.g., later used for disciplinary attendance enforcement rather than health), or for a change in institutional leadership that weakens the privacy safeguards currently designed in. This is a legitimate concern, and the honest answer is that technical safeguards (RBAC, k-anonymity, audit logs) reduce but do not eliminate this risk — institutional policy, data-retention limits, and governance oversight would need to accompany any real deployment, not just the software itself.

**Q17. How would you defend the choice to build custom algorithms instead of using a proven library like NetworkX?**
Two separate justifications, not one: pedagogically, per the Methodology, the project is explicitly scoped to demonstrate DSA competency, and using NetworkX would hide exactly the graph/BFS/Union-Find/heap logic the project exists to demonstrate. Practically, custom implementations mean every traversal, decay function, and aggregation rule is fully inspectable and explainable to a reviewer or auditor line by line, rather than trusting an external library's internals — a genuine advantage for a system whose defensibility depends on transparency.

**Q18. Isn't a 5-person-team (well, 4-person) academic prototype too small in scope to say anything meaningful about real institutional deployment?**
The pilot is deliberately scoped small (one division, then two) precisely so its claims are honest: it demonstrates that the architecture, algorithms, and privacy model work correctly on real institutional data at a scale that can be fully verified (seeded ground truth, exhaustive end-to-end testing), rather than claiming untested nation-scale readiness. The Improvements document is explicit and separate about exactly what would need to change (async processing, more roles, indexing, possibly Wi-Fi-assisted presence) to go from this verified pilot to a full-university deployment — the two are intentionally not conflated.

**Q19. What would falsify your claim that this system is better than existing approaches?**
If, on real deployment, the timetable-presence assumption turned out to miss the *majority* of actual transmission-relevant contact (e.g., most real transmission happening in unscheduled settings like dorms and dining halls rather than classrooms), the core "no new infrastructure needed" advantage would be undermined, since the system would then be systematically blind to where most exposure actually happens. This is exactly why Hartvigsen's residential-network finding (paper 14) is treated as a real, acknowledged gap rather than dismissed, and why the Improvements document proposes extending coverage rather than assuming the classroom-only model is sufficient forever.

**Q20. In one sentence, why does this project deserve to be taken seriously as more than a class assignment?**
Because it identifies a real, currently unmet institutional need (fast, privacy-respecting, infrastructure-free contact tracing for ordinary campus outbreaks, not just pandemic emergencies), grounds every major design decision in a specific gap named in peer-reviewed literature, and backs its claims with a fully working, end-to-end-tested implementation rather than a proposal or a slide deck.
