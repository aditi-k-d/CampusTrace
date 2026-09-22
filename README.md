# CampusTrace

CampusTrace is a college-level, role-based health surveillance and contact-tracing application. It derives possible contacts from academic structure—divisions, course enrolments, batches, rooms, and timetables—rather than GPS or Bluetooth tracking.

When a student reports an illness or a faculty member flags a health-related absence, the system traces possible exposures through the generated contact network. It presents graded risk alerts and response tools to the appropriate role while preserving privacy.

> **Academic project notice:** this repository and its demo seed use synthetic data only. The symptom checker is a triage aid, not a medical diagnosis tool.

## Key capabilities

- Role-based access for Students, Course Faculty, Class Teachers, Health Admins, and Institute Admins.
- Timetable-driven presence simulation and contact-edge generation.
- Forward, backward, and bidirectional BFS contact tracing with configurable depth.
- Risk classification using contact duration, temporal recency, location weighting, and hop decay.
- Private student exposure alerts and false-positive feedback.
- Health Admin contact-network visualisation, case analytics, priority queue, Disease Knowledge Base, and isolation-capacity workflow.
- Institute-level k-anonymized analytics and audit logs.

## Technology

- **Frontend:** React + Vite
- **Backend:** Flask + SQLAlchemy + JWT authentication
- **Database:** SQLite by default for local development; MySQL can be configured with `DATABASE_URL`.
- **Algorithms:** custom graph traversal, risk engine, Union-Find, and priority queue implementations.

## Quick start

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm

### 1. Start the backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

The API runs at `http://localhost:5000/api`.

To use MySQL instead of the local SQLite database, set `DATABASE_URL` before starting the backend:

```powershell
$env:DATABASE_URL = "mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/campustrace"
```

### 2. Populate the synthetic demo data

Keep the backend running, open a second terminal in the project root, and run:

```powershell
python scripts/dev_populate.py
```

The script resets the local development database by default, creates the demo users and academic structure, then generates three weeks of presence/contact data. Wait for its final summary before demonstrating the graph.

### 3. Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the URL shown by Vite, normally `http://localhost:5173`.

## Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Institute Admin | `admin@campustrace.edu` | `AdminPassword123!` |
| Health Admin | `healthadmin@campustrace.edu` | `HealthAdminPass123!` |
| Class Teacher (CE) | `ct_ce@campustrace.edu` | `ClassTeacherPass123!` |
| Class Teacher (IT) | `ct_it@campustrace.edu` | `ClassTeacherPass123!` |
| Course Faculty (CE) | `fac_ce_1@campustrace.edu` | `FacultyPass123!` |
| Bridging Faculty | `prof.bridge@campustrace.edu` | `BridgeFacultyPass123!` |

The seed script prints one sample student credential for each of the CE, IT, AI, and DS divisions when it completes.

## Role guide

### Student

- **Enrolled Courses:** view registered courses and assigned lab/tutorial batches.
- **Report Health Issue:** submit onset date, severity, known disease, and/or symptoms. This creates a `reported` case.
- **Health Status & History:** view only the student's own reports and their `reported` or `confirmed` state.
- **Exposure Alerts:** view private risk guidance, acknowledge an alert, or flag it as a false positive. The identity of the source contact is never disclosed.
- **Symptom Self-Assessment:** compare entered symptoms with the Disease Knowledge Base for non-diagnostic guidance.
- **Absence Flags:** confirm or deny a faculty-submitted absence flag.

### Course Faculty

- **Course Attendance & Health Summary:** enter a Course ID and date to view attendance and aggregated health counts for that course.
- **Flag Student Absence:** record a health-related or unexcused absence without assigning a medical diagnosis.
- **Absence Flags Raised:** review the state of submitted flags.

### Class Teacher

- **Division Overview:** view division-wide course attendance, presence, flag counts, and active health-case counts.
- **Absence Escalations:** review students with repeated absences across multiple courses during the rolling monitoring window.
- **Enrollment Approvals:** approve eligible batch, transfer, or elective-enrolment changes.

### Health Admin

- **Health Cases Tracker:** review reported cases and use **Confirm Case** when appropriate. A case may be traced before or after confirmation.
- **Contact Network Graph:** select a case, tracing direction, and depth, then choose **Trace Case**. Gold is the source case; red/orange/green nodes represent high/medium/low risk. Edge labels show contact duration.
- **Risk Breakdown:** use **View Breakdown** on a case to inspect the factors used in its risk classification.
- **Outbreak Analytics:** review cases, direct/secondary contacts, and the exposure-profile chart.
- **Priority Queue and Capacity:** prioritize high-risk contacts for isolation and manage available beds when facilities exist.
- **Disease Knowledge Base:** add or edit disease symptoms, precautions, and incubation periods.

### Institute Admin

- **Aggregated Analytics:** view division, course, department, event, and location summaries. Counts below the configured k-anonymity threshold are suppressed.
- **Structure & Timetables:** create divisions and rooms, then courses, batches, faculty assignments, and timetable slots.
- **User Role Management:** register staff/admin users and activate or deactivate accounts.
- **System Configuration:** set k-anonymity, default tracing depth, and default tracing direction.
- **Audit Log:** review sensitive operational and administrative actions.

## Suggested demo flow

1. Use a student account to show a health report or alert.
2. Use Course Faculty to show attendance and absence flagging.
3. Use Class Teacher to show a division pattern or escalation.
4. Use Health Admin to trace a seeded case. Case #5 is a good starting point after the seed completes.
5. Use Institute Admin to show privacy-preserving aggregated analytics and audit accountability.

## Validation

```powershell
# Frontend tests and production build
cd frontend
npm test
npm run build
```

Backend tests use the configured test database:

```powershell
cd backend
pytest app/tests -v
```
