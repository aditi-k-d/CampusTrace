# CampusTrace — API Contract

Base URL (local dev): `http://localhost:5000/api`

All request/response bodies are JSON. All protected endpoints require
`Authorization: Bearer <access_token>` from `/auth/login`.

**How to use this doc (per Tasks.md workflow):** sections marked
**BUILT** are implemented and tested — treat them as fixed unless you
have a reason to change them (open a PR to this doc first, per the
merge strategy). Sections marked **DRAFT** are proposed shapes for
routes that don't exist yet, based on `role_hierarchy.md`'s stated
capabilities — the owning person should confirm or revise the shape
here *before* building the route, so the frontend and backend agree
on it up front.

---

## Auth — **BUILT** (Person 1)

### `POST /auth/register`

Registers a new user.

**Registration policy:** `student` can self-register freely. Every
other role requires the caller to already be an authenticated
`institute_admin` — except the very first `institute_admin` account
ever created, which is allowed unauthenticated as a one-time
bootstrap.

Request:
```json
{
  "name": "string, required",
  "email": "string, required, unique",
  "password": "string, required",
  "role": "student | course_faculty | class_teacher | health_admin | institute_admin, required",
  "division_id": "int, required for student, optional otherwise"
}
```

Response `201`:
```json
{ "id": 1, "name": "...", "email": "...", "role": "student" }
```

Errors: `400` missing/invalid fields, `409` email already registered,
`403` caller not authorized to create this role.

### `POST /auth/login`

Request:
```json
{ "email": "string", "password": "string" }
```

Response `200`:
```json
{
  "access_token": "jwt string",
  "user": { "id": 1, "name": "...", "email": "...", "role": "student" }
}
```

Errors: `400` missing fields, `401` invalid credentials.

JWT claims include `role` and `division_id` — every downstream route
should read the role from the token via `@role_required(...)`, never
trust a role passed in the request body.

### `GET /auth/me`

Requires a valid token. Response `200`:
```json
{ "id": 1, "name": "...", "email": "...", "role": "student", "division_id": 1 }
```

---

## Student — **DRAFT** (Person 2, confirm before building)

All routes below require `@role_required("student")` and act only on
the calling student's own data — per role_hierarchy.md, a student can
never see another student's data.

| Method & Path | Purpose | Request | Response |
|---|---|---|---|
| `POST /student/register-batches` | Select batch for each lab/tutorial course at first login | `{ "batch_selections": [{"course_id": 1, "batch_id": 2}, ...] }` | `201` list of created enrollments |
| `GET /student/courses` | View own enrolled courses (read-only) | — | `200` list of courses/batches |
| `POST /student/health-report` | Report own illness | `{ "disease_id": 3 \| null, "custom_symptoms": "string" \| null, "onset_date": "YYYY-MM-DD", "severity": "mild\|moderate\|severe" }` | `201` created health_record; triggers tracing_service + alert_service server-side |
| `GET /student/alerts` | View own exposure alerts | — | `200` list of alerts (risk level, symptoms, precautions — never who exposed them, per role_hierarchy.md) |
| `POST /student/alerts/<id>/acknowledge` | Acknowledge a received alert | — | `200` |
| `POST /student/alerts/<id>/false-positive` | Flag an alert as a false positive | — | `201` feedback row created |
| `GET /student/absence-flags` | View absence flags raised against them | — | `200` list, pending ones need a response |
| `POST /student/absence-flags/<id>/respond` | Confirm/deny a faculty absence flag | `{ "confirm": true \| false }` | `200` |
| `POST /student/self-assessment` | Rule-based triage tool (available any time, not tied to reporting) | `{ "symptoms": ["string", ...] }` | `200` `{ "guidance": "string", "recommended_action": "string" }` |

---

## Course Faculty — **DRAFT** (Person 3, confirm before building)

Requires `@role_required("course_faculty", "class_teacher")` scoped to
courses the faculty member is assigned to via `FacultyCourseAssignment`.

| Method & Path | Purpose | Request | Response |
|---|---|---|---|
| `GET /faculty/courses/<course_id>/attendance` | Attendance for own course/batch sessions | query: `?date=YYYY-MM-DD` | `200` list of present users |
| `GET /faculty/courses/<course_id>/health-summary` | Aggregate health status (counts only, never individual diagnoses) | — | `200` `{ "total": 40, "under_observation": 2 }` |
| `POST /faculty/absence-flags` | Flag a student absent for health reasons | `{ "student_id": 1, "course_id": 2, "flagged_date": "YYYY-MM-DD", "reason_category": "string" }` | `201` |
| `GET /faculty/absence-flags` | Status of flags they've raised | — | `200` list with `state` |

## Class Teacher — **DRAFT** (Person 3, confirm before building)

Everything Course Faculty can do, at division level, plus:

| Method & Path | Purpose | Request | Response |
|---|---|---|---|
| `GET /class-teacher/division-pattern` | Division-wide attendance/health pattern across all courses | — | `200` |
| `GET /class-teacher/escalations` | Students showing a cross-course absence pattern | — | `200` list |
| `POST /class-teacher/enrollment-changes/<id>/approve` | Approve a batch/elective enrollment change | — | `200` |

---

## Health Admin — **DRAFT** (Person 4, confirm before building)

Requires `@role_required("health_admin")`. Fine-grained access here is
audited — every call should write an `AuditLog` row.

| Method & Path | Purpose | Request | Response |
|---|---|---|---|
| `GET /health-admin/cases` | All reported/flagged cases across divisions | query filters: `?status=`, `?disease_id=` | `200` list |
| `POST /health-admin/cases/<id>/confirm` | Confirm or reclassify a case | `{ "disease_id": 3 }` | `200` |
| `GET /health-admin/contact-graph/<case_id>` | Full contact graph / cluster viz for a case | query: `?direction=forward\|backward\|both&max_depth=2` | `200` — calls `tracing_service.trace_case()` (Person 1) |
| `POST /health-admin/contact-graph/<case_id>/retrace` | Manually re-trigger tracing with adjusted depth/direction | `{ "direction": "...", "max_depth": 3 }` | `200` |
| `GET /health-admin/disease-kb` | List KB entries | — | `200` list |
| `POST /health-admin/disease-kb` | Add a KB entry | `{ "name": "...", "symptoms": "...", "preventive_measures": "...", "incubation_period_days": 5 }` | `201` |
| `PATCH /health-admin/disease-kb/<id>` | Edit a KB entry | partial fields | `200` |
| `GET /health-admin/capacity` | Isolation/health-center capacity | — | `200` list of facilities with occupied/total |
| `POST /health-admin/capacity/<id>/allocate` | Allocate a bed via priority queue | `{ "user_id": 1 }` | `201` — uses `priority_queue.py` (Person 1) via `capacity_service.py` (Person 4) |
| `POST /health-admin/feedback/<alert_id>/review` | Review a false-positive flag, adjust weights | `{ "adjust_weight": true }` | `200` |

## Institute Admin — **DRAFT** (Person 4, confirm before building)

Requires `@role_required("institute_admin")`.

| Method & Path | Purpose | Request | Response |
|---|---|---|---|
| `GET /institute-admin/dashboards/aggregate` | K-anonymized dashboards across divisions | — | `200` — counts below `k_anonymity_threshold` suppressed server-side |
| `POST /institute-admin/divisions` | Add a division | `{ "name": "...", "branch": "...", "year": 2 }` | `201` |
| `POST /institute-admin/courses` | Add a course | `{ "division_id": 1, "code": "...", "name": "...", "course_type": "theory\|lab\|tutorial" }` | `201` |
| `POST /institute-admin/timetable-slots` | Add a timetable slot | `{ "course_id": 1, "room_id": 1, "batch_id": null, "day_of_week": 0, "start_time": "09:00", "end_time": "10:00" }` | `201` |
| `GET /institute-admin/system-config` | View current k-anon threshold / tracing defaults | — | `200` |
| `PATCH /institute-admin/system-config` | Update system-wide settings | `{ "k_anonymity_threshold": 5, "default_tracing_depth": 2 }` | `200` — maps to `SystemConfig` (Person 1) |
| `GET /institute-admin/audit-log` | View audit log | query: `?user_id=&action=&from=&to=` (paginate: `?limit=&cursor=`) | `200` |

---

## Conventions for every new route (all owners)

- Read the role from the JWT via `@role_required(...)` — never from
  the request body.
- Error shape is always `{ "error": "message" }` with an appropriate
  status code (`400` bad input, `401` no/invalid token, `403` wrong
  role, `404` not found, `409` conflict).
- Any endpoint returning more than ~50 rows (audit log, cases, alerts
  lists) should support `?limit=` and `?cursor=` pagination —
  don't return unbounded lists once real data volume shows up.
- If you need an endpoint that isn't in this doc yet, add it here
  first (as a PR) so the shape gets confirmed before it's built
  against, per the Tasks.md merge strategy.