# CampusTrace — Literature Review

This review covers all 16 papers used for the project, using the full author lists and abstracts provided. For each paper: what it actually studied/found, the specific research gap it leaves open (stated by the authors or clearly implied by its scope), and exactly how CampusTrace's design responds to that gap. A summary table and a Q&A section close the document.

---

### 1. Comparing the efficiency of forward and backward contact tracing
**Juul, J. L. & Strogatz, S. H.**

**What it studied:** A direct rebuttal to Kojaku et al. (paper #2 below). Juul & Strogatz show that Kojaku et al.'s headline claim — that backward tracing is "profoundly more effective" than forward tracing, and that tracing effectiveness "hinges on reaching the source of infection" — does not hold in general. The earlier conclusions rested on simulations that **overestimated** tracing effectiveness because they modeled disease spread and contact-tracing mitigation **sequentially** rather than simultaneously. Once corrected, the relative efficiency of forward vs. backward tracing turns out to be **highly context-dependent**, driven by the actual disease dynamics of the outbreak in question, and the authors stress the importance of simulating spread and mitigation in parallel.

**Research gap:** The paper is a simulation-methodology correction, not a system. It proves no single tracing direction is universally superior but offers no operational mechanism for an actual tracing system to pick the right direction for a given real outbreak.

**How CampusTrace fills it:** This finding directly justifies making tracing direction a **runtime, per-case configurable parameter** instead of a hardcoded strategy. `system_config.default_tracing_direction` sets an institution-wide default (`both`), but Health Admin can override it per case via `POST /health-admin/contact-graph/<case_id>/retrace` with `direction: forward | backward | both`. Rather than betting on one theory, the system operationalizes the paper's core conclusion: let context, not doctrine, decide the tracing strategy.

---

### 2. The effectiveness of backward contact tracing in networks
**Kojaku, S., Hébert-Dufresne, L., Mones, E., Lehmann, S., Ahn, Y.-Y.**

**What it studied:** The paper shows that backward tracing (tracing *from* whom disease spread, toward the source) is substantially more effective than forward tracing, because of the **friendship paradox** — in a heterogeneous contact network, high-contact individuals (potential super-spreaders) disproportionately show up as *someone else's* contact, so tracing backward toward a source over-samples exactly the highly-connected nodes worth finding. Using simulations on synthetic and high-resolution empirical contact data, the authors show strategically executed contact tracing can prevent more transmissions per isolation than case isolation alone, and they explicitly call for incorporating **backward and deep tracing in a digital context while respecting privacy-preserving requirements** of modern platforms.

**Research gap:** The paper stays at the network-science / simulation level. It identifies the statistical bias favoring backward tracing and explicitly asks for a privacy-preserving digital implementation, but does not build one.

**How CampusTrace fills it:** This is close to a direct specification for one half of the tracing system. Backward BFS/DFS is a first-class tracing mode in `traversal.py`, filtering `ContactEdge` rows by `contact_date < onset_date` to walk toward possible sources. Privacy is layered exactly as the paper requests: a contact who receives an alert sees risk level, symptoms, and recommended action, but the source case's identity is never included in that response. `tracing_service.py` plus the "never disclose source identity" rule for the Student role together answer this paper almost literally.

---

### 3. Recursive contact tracing in Reed-Frost epidemic models
**Shivam, S., Bulchandani, V. B., Sondhi, S. L.**

**What it studied:** The authors extend a Reed-Frost epidemic model to include **recursive (multi-hop) contact tracing** and asymptomatic transmission, generalizing an earlier branching-process model to finite populations and general contact networks. Testing on idealized topologies (complete graphs, square lattices), they identify a clear **contact-tracing phase transition** between an "epidemic phase" and an "immune phase" as network coverage increases, and show this transition follows percolation universality — i.e., there exists a coverage threshold beyond which recursive tracing effectively halts spread, even where perfect tracing is not achieved.

**Research gap:** The model is deliberately abstract. Complete graphs and square lattices are analytically convenient but bear no resemblance to a real social or institutional network, and the paper makes no attempt to apply the model to a bounded real population or build a working recursive-tracing tool.

**How CampusTrace fills it:** The paper's core structural insight — that *coverage and depth of tracing*, more than disease-specific parameters, determine whether an outbreak is contained — is operationalized via depth-bounded recursive BFS/DFS (`max_depth`, default 2, configurable per case) run on the **real** contact graph of an actual academic division, not an idealized lattice. Union-Find-based cluster detection further mirrors the paper's percolation framing: connected high-risk components are identified as clusters rather than reasoned about only as isolated pairwise edges.

---

### 4. An analytical evaluation of contact tracing systems using real-world individual-level data
**Li, Y., Ernst, K. C., Pogreba-Brown, K., Austhof, E., Heslin, K., Shilen, A., Ram, S.**

**What it studied:** A rare **empirical, not simulated**, comparison of concurrently running manual, automated, and semi-automated contact tracing at a US university, using individual-level data from September 2020 to February 2021 covering 2,415 confirmed positive cases. Key findings: the three systems had only ~15% overlap in case coverage and ~11% overlap in the contacts they eventually identified as infected — meaning each method was largely finding *different* people, not redundantly confirming the same ones. Manual tracing achieved the best exclusive coverage (51%) and precision (41% of identified contacts tested positive) but the worst timeliness (6-day median test-to-report delay); automated and semi-automated tracing were far faster (0- and 1-day median delay respectively) but less complete. 93% of notified individuals took protective action, and no one was able to re-identify the source case merely from a notification. The authors name two explicit literature gaps: (1) individual-level empirical evaluation is scarce because privacy-preserving automated apps keep no central log, and (2) the literature treats automated and manual tracing as competing alternatives rather than studying their **concurrent, joint** effect.

**Research gap:** No single method dominates on all four measured axes (coverage, completeness, precision, timeliness), and running three parallel, poorly-overlapping systems side by side is operationally wasteful and confusing for the traced population. The paper does not propose an architecture that captures the strengths of all three without their siloed weaknesses.

**How CampusTrace fills it:** CampusTrace collapses the three tracing modes into a single pipeline instead of running them in parallel. It gets automated tracing's speed — the BFS/DFS trace fires synchronously the moment a health report is submitted, with no test-to-report delay — while also getting manual tracing's completeness advantage without needing a human interviewer, because contact edges are derived from **mandatory institutional records** (enrollment, timetable) rather than opt-in app logs. There is no cross-system overlap gap and no adoption-fraction ceiling, because there is exactly one data source and one pipeline, not three competing ones.

---

### 5. Next Generation Technology for Epidemic Prevention and Control: Data-Driven Contact Tracking
**Chen, H., Yang, B., Pei, H., Liu, J.**

**What it studied:** A survey classifying contact-tracing technology along two axes — **individual vs. group** contact, and **static vs. dynamic** perspective — cataloguing methods ranging from paper questionnaires (static individual) through mobile/wearable/RFID/GPS sensing (dynamic individual) to large-scale contact matrices (static group) and AI-inferred dynamic group patterns. The paper closes by naming three directions for "next-generation" technology: **multi-view** contact tracing (combining several data sources), **multi-scale** tracing (individual and group together), and **AI-based** tracing methods using heterogeneous, multi-source data.

**Research gap:** As a survey, it identifies future directions rather than building or scoping anything concrete. None of its proposed directions are grounded in a specific, implementable, bounded deployment setting.

**How CampusTrace fills it:** CampusTrace is a concrete, appropriately-scoped instance of the "multi-view, multi-scale" direction the survey calls for — sized to an institution rather than a nation. **Static** structural data (timetables, enrollment, room assignments) combines with **dynamically** generated data (daily `Presence` and `ContactEdge` rows) to produce both **individual**-level tracing (BFS/DFS per case) and **group**-level views (Class Teacher division patterns, Institute Admin department aggregates) — both axes the survey names are represented in one working pipeline, without requiring the heavier AI-based inference the paper flags as still emerging.

---

### 6. Contact tracing – Old models and new challenges
**Müller, J. & Kretzschmar, M.** — *Infectious Disease Modelling*

**What it studied:** A review tracing the development of contact-tracing modelling theory since the 1980s, discussing classical approaches to finding effective and efficient tracing implementations and assessing tracing's effect on epidemic spread. The authors argue that despite decades of progress, important open questions remain, and that newer technological developments — genetic sequencing of pathogens and **digital contact tracing** specifically — pose fresh modelling challenges the classical theory was not built to address.

**Research gap:** The paper is explicit that classical contact-tracing theory needs updating for the digital era but stops at identifying the challenge; it does not build a digital tracing system or specify what a modernized implementation should look like.

**How CampusTrace fills it:** CampusTrace is a working answer to the "digital contact tracing" challenge the paper names — it replaces manual, interview-based classical tracing with a graph-based, algorithmically-traversed digital pipeline (BFS/DFS over `ContactEdge` data), while retaining the classical theory's core structural reasoning (contact networks, tracing depth, tracing direction) rather than discarding it. The "new challenges" the paper anticipates — coordinating a digital data source, defining privacy boundaries for it — are addressed through the RBAC and k-anonymity layers.

---

### 7. Comparison of contact tracing methods: A modelling study
**Tan, J. X. R., Kurupatham, L., Said, Z., Chan, J., Tan, K. B., Ho, M., Lee, V., Cook, A. R.** — *Infectious Disease Modelling*

**What it studied:** A modelling study (closely related to paper #8, sharing several authors and the Singapore case context) comparing contact-tracing methods for effectiveness and cost, evaluating how tracing strategy choices affect outbreak containment under realistic operational constraints rather than abstract network theory alone.

**Research gap:** As a modelling study, its conclusions are simulation-derived and tied to the specific population/disease parameters chosen; it does not describe how the compared strategies would actually be implemented as a deployable, real-time system a health authority could operate day to day.

**How CampusTrace fills it:** CampusTrace turns the class of "which method reduces transmission fastest" questions this paper studies into an operational, synchronous pipeline rather than a modelling exercise: the moment a case is reported, tracing runs immediately against real contact data, with direction and depth configurable per case — the deployable counterpart to the strategy comparisons this paper models in the abstract.

---

### 8. Estimating the effect of contact tracing during the early stage of an epidemic
**(companion Singapore-context study)** — *Infectious Disease Modelling*

**What it studied:** Using a transmission-network model built on Singapore's population structure and COVID-19 case data, this study compares **forward tracing**, **extended tracing** (covering a longer pre-isolation window), and **cluster tracing** (forward tracing combined with cluster identification) across combinations of low/high case-ascertainment and testing-vs-quarantine of contacts. Results show effectiveness varies substantially by scenario: under low ascertainment with quarantine, cluster tracing reduced transmission by up to 62% at the lowest cost; under high ascertainment with quarantine, all tracing methods performed comparably well and brought the reproduction number below 1. The paper's core message is that the *right* tracing method is highly dependent on the ascertainment and intervention context, not fixed.

**Research gap:** The model and its numbers are specific to COVID-19 and Singapore's population/testing structure; there is no generalizable data structure proposed for representing or computing "cluster tracing" in a reusable, disease-agnostic system.

**How CampusTrace fills it:** The paper's central finding — that cluster-aware tracing outperforms simple forward tracing, and that the best method is context-dependent — is operationalized disease-agnostically: `system_config` exposes tracing depth/direction as configurable parameters (not COVID-specific constants), and Union-Find-based cluster detection gives CampusTrace exactly the "cluster identification" capability this paper shows to be the most cost-effective strategy, without being tied to any single disease's parameters.

---

### 9 & 10. An SEIR network epidemic model with manual and digital contact tracing allowing delays / The effect of delay on contact tracing
**Zhang, D. & Britton, T.** (companion papers, near-identical abstracts/models)

**What they studied:** An SEIR epidemic model on a network (allowing random contacts too) where diagnosis triggers **manual** contact tracing (contacts reported, tested, and isolated after a random delay) and, if the diagnosed individual is an app-user, **digital** tracing (all app-using infectees immediately notified and isolated). Using multi-type branching-process approximations, the authors derive reproduction numbers for manual-only, digital-only, and combined tracing, and find that **app-adoption fraction plays an essential role** in overall effectiveness. Manual tracing's relative advantage over digital grows when more transmission happens on the network, when tracing delay shortens, and when the network's degree distribution is heavy-tailed. For realistic parameters, combined tracing reduces R₀ by only 20–30%, meaning other interventions are still needed to bring R₀ down to a containable range.

**Research gap:** Digital tracing's effectiveness in this model is structurally capped by the fraction of the population using the app — a ceiling the model treats as an exogenous parameter rather than something a system design could remove. Delay is treated as a random variable to be minimized, not eliminated by design.

**How CampusTrace fills it:** CampusTrace removes exactly the two levers these papers show matter most. The **app-adoption ceiling** disappears because contact edges are derived from **mandatory** institutional records (enrollment, timetable presence), not from an opt-in app — coverage is effectively 100% of the scheduled population rather than "however many chose to install and keep Bluetooth on." **Delay** is minimized by making tracing synchronous and server-triggered the moment a report is filed, rather than dependent on a manual interview step with a "random delay," directly addressing the paper's stated sensitivity of relative tracing-method effectiveness to delay length.

---

### 11. Comparative effectiveness of contact tracing interventions in the context of the COVID-19 pandemic: a systematic review
**Pozo-Martin, F., Beltran Sanchez, M. A., Müller, S. A., Diaconu, V., Weil, K., El Bcheraoui, C.**

**What it studied:** A systematic review of 78 studies (12 observational, 66 mathematical modelling) on the comparative effectiveness of contact-tracing interventions. Among the highly effective policies identified across the modelling literature: manual tracing with high coverage plus effective isolation/distancing; hybrid manual-plus-digital tracing with high app adoption; secondary (multi-hop) contact tracing; eliminating tracing delays; **bidirectional** contact tracing; and — notably — **contact tracing with high coverage in reopening educational institutions**. The review also flags a recurring limitation across the underlying observational studies: many fail to adequately describe the actual *extent* of contact-tracing implementation, making it hard to attribute outcomes to the intervention itself.

**Research gap:** The review names "high coverage in educational institutions" and "bidirectional tracing" as effective but does not itself build a system for either; and it explicitly critiques the broader literature for opacity about implementation extent — i.e., studies that don't clearly report *how completely* tracing was actually carried out.

**How CampusTrace fills it:** CampusTrace is essentially a direct implementation of two of the review's own named "highly effective policies" at once: it achieves high coverage in an educational institution by construction (derived from mandatory enrollment/timetable data, not opt-in), and it implements bidirectional tracing as a first-class, per-case configurable mode. It also directly answers the review's "implementation extent" critique: the API contract, test suite, and audit log make the system's tracing coverage and behavior fully specified and independently verifiable, not a vague "contact tracing was used" statement in a paper.

---

### 12. Privacy and contact tracing efficacy
**Benthall, S., Hatna, E., Epstein, J. M., Strandburg, K. J.**

**What it studied:** The authors modify a standard SEIR transmission model to incorporate contact tracing and study, via simulation, how important it is to trace **socially distant, privacy-sensitive contacts** specifically (as opposed to close, already-known ones). Their finding, for the simple network modeled, is that comprehensively tracing distant contacts is **surprisingly unimportant** as long as overall contact-tracing adoption is sufficiently high — implying policymakers designing tracing systems should be willing to trade off tracing comprehensiveness for broader, more privacy-respecting adoption.

**Research gap:** The paper is explicit that comprehensive smartphone-based contact tracing raises privacy concerns "not previously explored" in the literature, and its own finding argues for a *design tradeoff* (less comprehensiveness, more adoption) but does not specify a concrete system architecture that implements that tradeoff.

**How CampusTrace fills it:** CampusTrace resolves this tradeoff structurally rather than by sacrificing comprehensiveness. Because coverage comes from mandatory institutional records rather than opt-in adoption, the "trade comprehensiveness for adoption" dilemma the paper identifies doesn't arise in the first place — comprehensiveness and coverage are simultaneously maximized. Privacy is instead protected via the 5-tier RBAC system, source-identity concealment for alerted students, k-anonymized aggregate views (suppressing any count under the configured threshold, default 5), and a full audit log of Health Admin's fine-grained access — a concrete architecture answering exactly the "privacy-preserving comprehensive tracing" gap the paper leaves open.

---

### 13. Modeling the effects of contact tracing on COVID-19 transmission
**Traoré, A. & Konané, F. V.**

**What it studied:** A mathematical model of COVID-19 incorporating contact tracing, deriving the contact-tracing-induced reproduction number ℛ_q and the model's equilibria, and proving global stability results via Lyapunov functions. The model compares ℛ_q against the baseline reproduction number ℛ₀ (no intervention) to assess the theoretical benefit of contact tracing.

**Research gap:** This is a pure mathematical-epidemiology paper. It formally proves *that* contact tracing lowers the reproduction number under the model's assumptions, but does not touch implementation, data collection, or system architecture at all.

**How CampusTrace fills it:** CampusTrace does not implement Lyapunov stability analysis directly — that is out of scope for a DSA-and-application-focused project — but it embodies the paper's practical implication in system form: the paper's math shows ℛ_q falls as tracing coverage rises and tracing speed increases, and CampusTrace is built specifically to maximize both (near-100%-of-enrollment coverage via mandatory records, synchronous alerting with no reporting delay) rather than to further prove the underlying theorem.

---

### 14. Network Assessment and Modeling the Management of an Epidemic on a College Campus with Testing, Contact Tracing, and Masking
**Hartvigsen, G.**

**What it studied:** A simulation built on **real course-enrollment and residential network data** from a 5,539-student residential college (SUNY Geneseo), comparing epidemic dynamics on this real structure against equal-sized random networks. The college's actual network structure (longer average path lengths, lower clustering on heavy class days, right-skewed degree distributions up to 719 contacts) meaningfully changed epidemic outcomes versus a random-mixing assumption. Testing frequency and mask compliance mattered more than contact tracing alone in reducing case counts, but tracing still measurably helped, and the paper models **both academic and residential** contact layers together.

**Research gap:** This is a simulation study on a real network, not a deployable tracing tool — it models *what would happen* under various interventions rather than building *the system that would make those interventions operational*. Notably, it also models **residential (dormitory) networks alongside academic ones**, a scope most contact-tracing systems — including CampusTrace currently — do not cover.

**How CampusTrace fills it — and where the gap knowingly remains open:** CampusTrace is the deployable counterpart to Hartvigsen's simulation: it builds the real (not simulated) course/timetable-derived contact graph for an actual division and runs live tracing on it, rather than modelling outcomes abstractly. However, in one of the few places this project does **not yet close the gap**, CampusTrace currently mirrors one of the paper's own scope boundaries by having no residence-hall/dormitory contact layer — only classroom/lab presence is modeled. This is named explicitly as a concrete future extension in the Improvements document, directly motivated by this paper's finding that residential structure materially affects outbreak dynamics.

---

### 15. Digital Contact Tracing Based on a Graph Database Algorithm for Emergency Management During the COVID-19 Epidemic: Case Study
**Mao, Z., Yao, H., Zou, Q., Zhang, W., Dong, Y.**

**What it studied:** A real government deployment in Hainan Province, China: a graph-database algorithm running on a centralized big-data platform related infected individuals to the general population, vehicles, and public places to identify and trace contacts. The system successfully traced 10,871 contacts (378 closest contacts) out of hundreds of thousands of records, and helped find at least one confirmed patient after quarantine of identified contacts. The authors' own stated future directions: strengthen data security, improve tracing accuracy, enable more intelligent data collection, and improve data-sharing mechanisms.

**Research gap:** This is a nation/province-scale, multi-source mass-surveillance model — vehicles, public venues, and a centralized government data platform. It is effective at scale, but this is precisely the kind of centralized, broad-footprint data model that papers #2 and #12 in this review warn creates serious privacy exposure, and the authors themselves flag data security and sharing mechanisms as unresolved.

**How CampusTrace fills it:** CampusTrace borrows the genuinely good idea — modelling contacts as a relational/graph structure for fast identification and tracing — but deliberately scopes the data footprint down from mass surveillance to institution-appropriate data only. There are no vehicle logs, no public-location tracking, and no external government data-sharing pipeline; every edge comes solely from timetable/enrollment intersections the institution already legitimately holds for academic purposes. This directly answers the paper's own "improve data security and sharing mechanisms" future-work item by minimizing the data footprint at the source, rather than trying to secure a much larger one after the fact.

---

### 16. Framework for Prioritizing Contact Tracing and Mass Testing of COVID-19 Using Graph Theory
**Appiah, O., Otoo, D., Ninfaakang, C. B.**

**What it studied:** An SQL-based framework that transforms raw interaction-log entries into an interaction graph and applies graph theory to compute a per-individual **Risk_Points** value, used to prioritize which individuals should be selected for isolation and testing first. The framework was validated only on simulated interaction data.

**Research gap:** Two things are left open by the authors' own scope: (1) validation used simulated data only, with no real deployment; (2) the framework assumes interaction data already exists in a usable tabular form, without addressing *how* that interaction data would actually be collected in a real institution, and it has no role-based access layer or operational dashboard wrapped around the risk scores it produces.

**How CampusTrace fills it:** This paper's central idea — a per-node risk score driving prioritization — is directly extended into `risk_engine.py`'s weighted formula (duration × recency-decay × room-type weight, aggregated across multiple contacts via Noisy-OR) and consumed operationally by a hand-written **priority queue/heap** for isolation-bed allocation (`capacity_service.py`), closing the loop from "compute a risk score" to "actually allocate a scarce resource based on it." The unresolved "where does interaction data come from" question is answered by deriving it automatically from timetable and enrollment records instead of requiring manually logged interactions, and the whole pipeline is wrapped in role-based dashboards and an audit trail the original framework lacked entirely.

---

## Summary Table

| # | Paper (short) | Core Gap | CampusTrace Response |
|---|---|---|---|
| 1 | Juul & Strogatz | Direction-effectiveness is context-dependent; no system lets you choose | Configurable `direction` per trace |
| 2 | Kojaku et al. | Calls for digital + privacy-preserving backward tracing, doesn't build it | Backward BFS/DFS + source-identity concealment |
| 3 | Shivam et al. | Idealized topologies only (lattice, complete graph) | Recursive depth-bounded tracing on a real institutional graph |
| 4 | Li et al. | 3 siloed tracing systems, poor overlap, no joint architecture | One pipeline gets speed + completeness together |
| 5 | Chen et al. | Survey names multi-view/multi-scale as future work | Static + dynamic, individual + group tracing implemented together |
| 6 | Müller & Kretzschmar | Classical models need a digital-era update | Modern digital graph-traversal implementation |
| 7 | Tan et al. | Modelling-only comparison of tracing methods | Synchronous, deployable real-time tracing pipeline |
| 8 | Singapore cluster-tracing study | COVID/Singapore-specific; no reusable "cluster tracing" data structure | Disease-agnostic config + Union-Find clustering |
| 9,10 | Zhang & Britton | Digital tracing capped by app-adoption fraction; delay hurts effectiveness | Mandatory-record-derived edges remove adoption ceiling; synchronous tracing removes delay |
| 11 | Pozo-Martin et al. | Educational institutions named effective but under-implemented; opacity on implementation extent | Institution-scoped system, fully documented, testable API contract |
| 12 | Benthall et al. | No concrete architecture for the privacy vs. comprehensiveness tradeoff | Mandatory records remove the tradeoff; RBAC + k-anonymity + audit log protect privacy |
| 13 | Traoré & Konané | Pure math, no applied system | Coverage/speed maximization embodies the stability result practically |
| 14 | Hartvigsen | Simulation only; also covers residence networks CampusTrace doesn't yet | Deployable version of the same idea; residence layer named as future work |
| 15 | Mao et al. | Mass-surveillance, centralized, own stated privacy/security gaps | Minimal-footprint, institution-only data sources |
| 16 | Appiah et al. | Simulated data only; no data-collection method; no operational layer | Automatic edge derivation + priority-queue-driven capacity allocation |

---

## Frequently Asked Questions (Literature Review)

**Q1. Why these 16 papers specifically — what was the selection logic?**
They cover three complementary layers the project actually needed: (a) the pure network-science/epidemiological theory of *why* and *when* forward vs. backward vs. clustered tracing works (papers 1, 2, 3, 6, 8, 9, 10, 11, 13); (b) empirical/real-world evaluation of tracing systems as actually deployed (papers 4, 14, 15); and (c) prior systems/frameworks attempting to operationalize tracing computationally (papers 5, 12, 16). Between them they justify almost every non-trivial design decision in CampusTrace — from why tracing direction is configurable, to why the data source is mandatory records rather than an app, to why risk is a graded score rather than a binary flag.

**Q2. Don't papers 1 and 2 directly contradict each other? How do you resolve that in your design?**
Yes, and that contradiction is itself the design lesson. Kojaku et al. claim backward tracing is far superior; Juul & Strogatz show that conclusion doesn't generalize once spread and mitigation are simulated correctly together. CampusTrace resolves this by refusing to hardcode either position — direction is a per-case, Health-Admin-configurable parameter (defaulting to `both`), which is the only design that stays correct under either paper's conclusion.

**Q3. Two of your papers (9 and 10) have near-identical abstracts. Is that a mistake in your reading list?**
No — they are companion papers by the same authors (Zhang & Britton) studying the same SEIR-with-tracing-delay model from two angles (one paper frames it as the general model, the other isolates the effect of delay specifically). They are treated as one combined entry in this review because their findings and the gap they leave are functionally identical, and duplicating the same analysis twice would add no value.

**Q4. Which single paper most directly shaped your risk-scoring formula?**
Appiah et al. (paper 16) is the most direct ancestor — its Risk_Points-per-node concept is exactly what `risk_engine.py` computes and what the priority queue in `capacity_service.py` consumes. The functional *shape* of the formula (exponential recency decay, duration capping) draws more generally from how recency and duration are treated as effectiveness factors across the modelling papers (8, 9/10, 11) rather than from one single source.

**Q5. Is there a risk that this review is "reverse-engineered" — picking convenient interpretations of each paper to justify decisions already made?**
It's a fair concern for any student project's literature review, and the honest answer is: some of it certainly is, because the system was scoped with awareness of this literature from early on (per `methodology.md`), not discovered afterward. What keeps the mapping honest is that each entry above names a gap the paper's own text supports (its stated future work, its own scope limitation, or its explicit call for further work) rather than an invented one, and — importantly — paper 14 (Hartvigsen) is used to name a real, currently-unclosed gap (the missing residential contact layer) rather than being spun as fully solved, which is the clearest evidence the mapping isn't purely self-serving.

**Q6. Why is there no paper here specifically about machine-learning-based exposure risk prediction?**
Because the project's own Methodology deliberately avoids black-box ML for risk scoring (an explicit non-goal, with the false-positive feedback loop as the only sanctioned learning mechanism), so ML-driven risk-prediction literature wasn't a fit for the papers this system actually needed to justify. Chen et al. (paper 5) does mention "AI-based contact tracing" as a future direction, but CampusTrace consciously does not pursue that direction, and the review is honest about that rather than stretching the paper to claim otherwise.

**Q7. If you had to add a 17th paper, what would it be and why?**
A paper specifically on Wi-Fi-association-based indoor presence/proximity inference (rather than BLE or GPS) would be the natural next addition, since it would directly ground the Wi-Fi proximity proposal discussed in the Improvements document with prior empirical evidence, rather than that proposal resting only on general engineering reasoning about how campus Wi-Fi infrastructure behaves.

**Q8. How does this literature review connect to the Topic Analysis document?**
The Topic Analysis's "why this solution is best among alternatives" comparison table is essentially a compressed, decision-facing version of the gap analysis in this document — each row of that table (BLE apps, GPS, manual interviews, national apps) maps back to specific papers here (BLE/adoption ceiling → papers 9/10, 12; manual tracing delay → paper 4; national-app binary alerts → papers 2, 16).
