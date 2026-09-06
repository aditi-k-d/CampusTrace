# CampusTrace — Role Hierarchy

## Hierarchy Overview

```
Institute Admin   (policy / system configuration / oversight)
      │
Health Admin      (operational health authority)
      │
Class Teacher     (division-level authority)
      │
Course Faculty    (course/batch-level authority)
      │
Student           (base level)
```

Note: in the single-division pilot, Class Teacher and Course Faculty will look similar since there's only one division to compare against. The distinction becomes meaningful once a second division is introduced (Phase 2), since Class Teacher's value is in seeing patterns *across* a student's courses, not within just one.

## Student

**Can view:**
- Own health status and history
- Own exposure alerts (risk level, symptoms, preventive measures, recommended action — never who exposed them)
- Own courses/batches (read-only, set at registration)
- Self-assessment tool (available any time, not tied to formally reporting an illness)

**Can do:**
- Register (first login): select division, then select batch for each lab/tutorial course (theory courses need no selection)
- Report own illness: known disease (autocomplete) or custom symptoms, onset date, severity
- Respond to a faculty absence flag (confirm/deny)
- Acknowledge received alerts
- Flag an alert as a false positive (feedback loop)

**Cannot:**
- See any other student's status, name, or health data
- See room-level or cluster-level aggregate data
- See admin/faculty dashboards

## Course Faculty

**Can view:**
- Attendance for their own course/batch sessions
- Aggregate health status summary for their own course/batch (counts only, e.g. "2 of 40 under observation" — not individual diagnoses)
- Status of absence flags they've raised (pending/confirmed/dismissed)

**Can do:**
- Flag a student as absent-for-health-reasons (reason category, not a diagnosis)
- Verify/respond if asked to confirm a student's self-reported status

**Cannot:**
- See other courses' or other faculty's data
- See full health records or symptom details
- Access contact graph or admin-level dashboards

## Class Teacher

**Can view:**
- Division-wide attendance/health pattern across all courses their division's students take (not just one course)
- Escalations when a student shows a cross-course absence pattern

**Can do:**
- Everything Course Faculty can do, at division level
- Approve batch/elective enrollment changes for their division

**Cannot:**
- See other divisions' data
- Access system-wide configuration or the Disease Knowledge Base

## Health Admin

**Can view:**
- All reported/flagged cases across divisions
- Full contact graph and cluster/hotspot visualizations (fine-grained — access is audited)
- Trend charts (daily new cases, active cases, recovery rate), disease-wise if multiple outbreaks are active
- Priority queue of high-risk contacts ranked by risk score

**Can do:**
- Confirm or reclassify a case (e.g., match a custom-symptom case to a known disease once confirmed)
- Add/edit entries in the Disease Knowledge Base (symptoms, preventive measures, incubation period)
- Manually trigger or adjust contact tracing (depth, direction) for a specific case
- Manage isolation/health-center bed capacity and allocate based on the priority queue
- Review flagged false positives and adjust risk weights accordingly

**Cannot:**
- Change system-wide configuration (k-anonymity threshold, global tracing defaults) — that's Institute Admin
- Add/remove user roles or manage timetables

## Institute Admin

**Can view:**
- Aggregated, k-anonymized dashboards across all divisions/departments (not room/individual level — even Institute Admin respects the privacy layer)
- Institution-wide outbreak trend reports
- Audit log — who accessed what, especially Health Admin's access to fine-grained data

**Can do:**
- Add/edit divisions, courses, rooms, and timetables
- Manage user roles/permissions (add/remove faculty, health admins)
- Configure system-wide parameters: k-anonymity threshold, default tracing depth
- Approve new Disease Knowledge Base entries at a policy level (if that sign-off step is used)

**Cannot:**
- Handle individual case confirmation or symptom review — that stays with Health Admin
- View room-level or individual-level contact data directly

## Summary Table

| Capability | Student | Course Faculty | Class Teacher | Health Admin | Institute Admin |
|---|---|---|---|---|---|
| Report own illness | ✅ | ❌ | ❌ | ❌ | ❌ |
| Flag others' absence | ❌ | ✅ (own course) | ✅ (own division) | ✅ | ❌ |
| Self-assessment tool | ✅ | ❌ | ❌ | ❌ | ❌ |
| Receive exposure alerts | ✅ | ❌ | ❌ | — | — |
| View individual health records | own only | status only (own course) | status only (own division) | ✅ (audited) | ❌ |
| View contact graph (fine-grained) | ❌ | ❌ | ❌ | ✅ | ❌ |
| View aggregated k-anon dashboards | ❌ | ❌ | ❌ | ✅ | ✅ |
| Manage Disease Knowledge Base | ❌ | ❌ | ❌ | ✅ (add/edit) | ✅ (approve, if used) |
| Manage capacity/isolation | ❌ | ❌ | ❌ | ✅ | ❌ |
| Add/edit timetables | ❌ | ❌ | ❌ | ❌ | ✅ |
| Configure system-wide settings | ❌ | ❌ | ❌ | ❌ | ✅ |
| Audit log access | ❌ | ❌ | ❌ | ❌ | ✅ |