# CampusTrace — Task Breakdown, Folder Ownership, and Merge Strategy

## Full Repository Structure (who owns what)

```
campustrace/
├── database/
│   └── schema.sql                          [Person 1]                                          ## done
│
├── backend/
│   ├── app/
│   │   ├── __init__.py                     [Person 1] app factory, blueprint registration      ## done
│   │   ├── config.py                       [Person 1] DB URI, secret key, env config           ## done
│   │   ├── extensions.py                   [Person 1] db, bcrypt, jwt manager init             ## done
│   │   │
│   │   ├── auth/
│   │   │   ├── routes.py                   [Person 1] /auth/register, /auth/login              ## done              
│   │   │   └── rbac.py                     [Person 1] @role_required decorator                 ## done
│   │   │
│   │   ├── models/
│   │   │   ├── user.py                     [Person 1]                                          ## done
│   │   │   ├── division.py                 [Person 1]                                          ## done
│   │   │   ├── timetable.py                [Person 1]                                          ## done
│   │   │   ├── enrollment.py               [Person 1]                                          ## done
│   │   │   ├── health_record.py            [Person 1] (schema owner; fields used by P2–P4)     ## done
│   │   │   ├── absence_flag.py             [Person 1]                                          ## done
│   │   │   ├── disease_kb.py               [Person 1]                                          ## done
│   │   │   ├── contact_edge.py             [Person 1]                                          ## done
│   │   │   ├── alert.py                    [Person 1]                                          ## done
│   │   │   ├── feedback.py                 [Person 1]                                          ## done
│   │   │   ├── capacity.py                 [Person 1]                                          ## done
│   │   │   └── audit_log.py                [Person 1]                                          ## done
│   │   │
│   │   ├── graph/
│   │   │   ├── graph.py                    [Person 1] Graph class (adjacency list)
│   │   │   ├── traversal.py                [Person 1] BFS/DFS forward + backward
│   │   │   ├── union_find.py               [Person 1] Disjoint Set, path compression
│   │   │   ├── risk_engine.py              [Person 1] weighted scoring formula
│   │   │   └── priority_queue.py           [Person 1] heap for capacity allocation
│   │   │
│   │   ├── services/
│   │   │   ├── presence_builder.py         [Person 1] Timetable+Enrollment → Presence
│   │   │   ├── graph_builder.py            [Person 1] Presence → ContactEdge
│   │   │   ├── tracing_service.py          [Person 1] wraps traversal.py for routes to call
│   │   │   ├── alert_service.py            [Person 1] generates Alert rows from tracing results
│   │   │   ├── disease_kb_service.py       [Person 4] symptom-matching, KB CRUD
│   │   │   └── capacity_service.py         [Person 4] bed allocation logic (uses priority_queue.py)
│   │   │
│   │   ├── routes/
│   │   │   ├── student.py                  [Person 2]
│   │   │   ├── faculty.py                  [Person 3] course faculty endpoints
│   │   │   ├── class_teacher.py            [Person 3] division-level endpoints
│   │   │   ├── health_admin.py             [Person 4]
│   │   │   └── institute_admin.py          [Person 4]
│   │   │
│   │   └── tests/
│   │       ├── test_graph.py               [Person 1]
│   │       ├── test_auth.py                [Person 1]
│   │       ├── test_student_routes.py      [Person 2]
│   │       ├── test_faculty_routes.py      [Person 3]
│   │       └── test_admin_routes.py        [Person 4]
│   │
│   └── requirements.txt                    [Person 1, appended to by others as needed]
│
├── frontend/
│   └── src/
│       ├── api/
│       │   ├── client.js                   [Person 1] axios instance, base URL, token header
│       │   ├── studentApi.js               [Person 2]
│       │   ├── facultyApi.js               [Person 3]
│       │   └── adminApi.js                 [Person 4]
│       │
│       ├── auth/
│       │   ├── Login.jsx                   [Person 1]
│       │   ├── Register.jsx                [Person 1]
│       │   └── ProtectedRoute.jsx          [Person 1] role-based route guard
│       │
│       ├── components/
│       │   ├── student/                    [Person 2] self-report form, alert card, self-assessment
│       │   ├── faculty/                    [Person 3] absence-flag form, class attendance view
│       │   └── admin/                      [Person 4] dashboards, Disease KB editor, capacity view
│       │
│       ├── pages/
│       │   ├── StudentDashboard.jsx        [Person 2]
│       │   ├── FacultyDashboard.jsx        [Person 3]
│       │   ├── ClassTeacherDashboard.jsx   [Person 3]
│       │   ├── HealthAdminDashboard.jsx    [Person 4]
│       │   └── InstituteAdminDashboard.jsx [Person 4]
│       │
│       └── App.jsx                         [Person 1 sets up routing shell; P2–P4 each add their own route line]
│
└── docs/
    ├── project_overview.md                 [Person 1]
    ├── methodology.md                      [Person 1]
    ├── role_hierarchy.md                   [Person 1]
    ├── api_contract.md                     [Person 1, kept updated as others build]
    └── workflow.md                         [Person 1]
```

**Rule of thumb for shared files** (`App.jsx`, `requirements.txt`, `__init__.py` blueprint registration): only ever *add* a line (a new import, a new route registration) — never rewrite the whole file. This is what keeps four people editing the same file across the project from turning into constant merge conflicts.

---

## Task List Per Person

### Person 1 — Foundation & Algorithms

| Task | Output file(s) |
|---|---|
| Finalize and commit schema | `database/schema.sql` |
| Flask app factory + config | `app/__init__.py`, `config.py`, `extensions.py` |
| Register/login endpoints | `auth/routes.py` |
| Role-based access decorator | `auth/rbac.py` |
| SQLAlchemy models for all tables | `models/*.py` |
| Graph class + BFS/DFS forward & backward | `graph/graph.py`, `graph/traversal.py` |
| Union-Find for cluster detection | `graph/union_find.py` |
| Risk scoring formula | `graph/risk_engine.py` |
| Priority queue/heap | `graph/priority_queue.py` |
| Nightly presence-generation job | `services/presence_builder.py` |
| Contact graph builder (Presence → Edges) | `services/graph_builder.py` |
| Tracing service (wraps traversal for route use) | `services/tracing_service.py` |
| Alert generation service | `services/alert_service.py` |
| Unit tests for all of the above | `tests/test_graph.py`, `tests/test_auth.py` |
| API contract doc (written early, updated as needed) | `docs/api_contract.md` |
| React auth shell + routing | `api/client.js`, `auth/Login.jsx`, `Register.jsx`, `ProtectedRoute.jsx`, `App.jsx` skeleton |

### Person 2 — Student Module

| Task | Output file(s) |
|---|---|
| Registration flow (division → batch selection) | `routes/student.py`, `components/student/` |
| Self-report illness endpoint + form | `routes/student.py`, `studentApi.js` |
| View own alerts endpoint + alert card UI | `routes/student.py`, `components/student/AlertCard.jsx` |
| Self-assessment (rule-based triage) interface | `components/student/SelfAssessment.jsx` |
| Acknowledge alert / flag false positive | `routes/student.py`, `studentApi.js` |
| Student dashboard page | `pages/StudentDashboard.jsx` |
| Route tests | `tests/test_student_routes.py` |

### Person 3 — Course Faculty + Class Teacher Module

| Task | Output file(s) |
|---|---|
| Course attendance view endpoint | `routes/faculty.py` |
| Absence-flag creation endpoint + form | `routes/faculty.py`, `components/faculty/AbsenceFlagForm.jsx` |
| Course-level aggregate health status view | `routes/faculty.py`, `FacultyDashboard.jsx` |
| Division-wide pattern view (Class Teacher) | `routes/class_teacher.py`, `ClassTeacherDashboard.jsx` |
| Batch/enrollment change approval endpoint | `routes/class_teacher.py` |
| Route tests | `tests/test_faculty_routes.py` |

### Person 4 — Health Admin + Institute Admin Module

| Task | Output file(s) |
|---|---|
| Case management (confirm/reclassify) endpoint | `routes/health_admin.py` |
| Disease Knowledge Base CRUD + symptom matching | `services/disease_kb_service.py`, `routes/health_admin.py` |
| Contact graph / cluster visualization endpoint | `routes/health_admin.py` (calls Person 1's graph/services) |
| Capacity tracker + priority-queue allocation | `services/capacity_service.py`, `routes/health_admin.py` |
| K-anonymity aggregation logic for admin views | `routes/institute_admin.py` |
| Timetable/division/course entry endpoints | `routes/institute_admin.py` |
| System config (k-anon threshold, tracing depth) | `routes/institute_admin.py` |
| Audit log viewer endpoint | `routes/institute_admin.py` |
| Both dashboard pages | `HealthAdminDashboard.jsx`, `InstituteAdminDashboard.jsx` |
| Route tests | `tests/test_admin_routes.py` |

---

## Merge Strategy

### Dependency order (this is what actually determines your timeline)

```
Person 1's foundation must merge to `dev` FIRST
        │
        ▼
Persons 2, 3, 4 branch off `dev` and build in PARALLEL
        │
        ▼
Each merges back to `dev` as their vertical slice completes
        │
        ▼
Integration testing on `dev` (all four together)
        │
        ▼
Tag and merge `dev` → `main`
```

Persons 2–4 **cannot meaningfully start** until Person 1's schema, auth/RBAC, and API contract exist — this is why Person 1's work is front-loaded in the phased plan. Give this a real deadline (end of Phase 1) so the other three aren't left waiting.

### Branch naming

```
feature/p1-auth-rbac
feature/p1-graph-engine
feature/p2-self-report
feature/p2-alerts-view
feature/p3-absence-flag
feature/p4-disease-kb
feature/p4-capacity-tracker
```

One branch per task from the tables above, not one giant branch per person — smaller PRs are easier to review and merge without conflict.

### PR review rule

Every PR needs at least one review before merging into `dev` — for a 4-person team, review can rotate (Person 2 reviews Person 3's PR, etc.), except Person 1's foundation PRs, which everyone should skim since all three others depend on them directly.

### How integration actually happens week to week

1. **Person 1 merges foundation pieces incrementally** (e.g., schema first, then auth, then graph modules) rather than one giant foundation PR — this lets Persons 2–4 start on the parts that are ready (e.g., start building UI against the schema while auth is still being finished) instead of blocking entirely
2. **API contract is the shared source of truth** — if Person 4 needs an endpoint that isn't in `docs/api_contract.md` yet, they add it to the doc first (as a PR) so Person 1 or whoever owns that route can confirm the shape before it's built against
3. **Weekly sync** — quick check: did any shared file change (schema, API contract, `App.jsx` routes)? Anyone whose module depends on a changed piece pulls `dev` and adjusts before continuing
4. **Shared files use additive-only edits** — e.g., in `App.jsx`, Person 2 only adds `<Route path="/student" ... />`, never restructures the whole router; same for `requirements.txt` (append, don't reorder) and blueprint registration in `app/__init__.py`

### End-of-phase integration checkpoint

At the end of each phase (per `methodology.md`), do a full merge of all four members' branches into `dev`, run the complete test suite together, and manually walk through one end-to-end flow (e.g., "student reports illness → contact gets alerted → admin sees it on dashboard") before tagging that phase as complete. This is where cross-module bugs (a field name mismatch between what Person 2's frontend expects and what Person 1's backend returns) actually surface — better to catch it at a planned checkpoint than during final demo prep.