"""
Tests for app/routes/faculty.py and app/routes/class_teacher.py.
Run: cd backend && pytest app/tests/test_faculty_routes.py -v
"""

from datetime import date, time, timedelta
import pytest

from app.extensions import db as _db
from app.models.division import Division, Room
from app.models.course import Course, Batch, FacultyCourseAssignment
from app.models.enrollment import Enrollment
from app.models.presence import Presence
from app.models.timetable import TimetableSlot
from app.models.health_record import HealthRecord
from app.models.absence_flag import AbsenceFlag
from app.models.disease_kb import DiseaseKB
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_admin(client):
    client.post("/api/auth/register", json={
        "name": "Admin", "email": "admin@campus.edu",
        "password": "adminpass", "role": "institute_admin",
    })
    resp = client.post("/api/auth/login", json={
        "email": "admin@campus.edu", "password": "adminpass",
    })
    return resp.get_json()["access_token"]


def _make_user(client, admin_token, name, email, role, division_id=None):
    headers = {"Authorization": f"Bearer {admin_token}"} if role != "student" else {}
    payload = {"name": name, "email": email, "password": "pass123", "role": role}
    if division_id:
        payload["division_id"] = division_id
    client.post("/api/auth/register", json=payload, headers=headers)
    resp = client.post("/api/auth/login", json={"email": email, "password": "pass123"})
    data = resp.get_json()
    return data["access_token"], data["user"]["id"]


def _setup_env():
    div1 = Division(name="CS-A", branch="CS", year=2)
    div2 = Division(name="CS-B", branch="CS", year=2)
    _db.session.add_all([div1, div2])
    _db.session.flush()

    c1 = Course(division_id=div1.id, code="CS101", name="Algo", course_type="theory")
    c2 = Course(division_id=div1.id, code="CS102", name="OS", course_type="theory")
    c_other = Course(division_id=div2.id, code="CS201", name="Networks", course_type="theory")
    _db.session.add_all([c1, c2, c_other])

    room = Room(name="Room 101", building="CS Bldg", capacity=40)
    _db.session.add(room)
    _db.session.flush()

    slot = TimetableSlot(course_id=c1.id, room_id=room.id, day_of_week=0, start_time=time(9, 0), end_time=time(10, 0))
    _db.session.add(slot)
    _db.session.commit()

    return div1.id, div2.id, c1.id, c2.id, c_other.id, room.id, slot.id


# ---------------------------------------------------------------------------
# Test Cases — Course Faculty Routes & Permissions
# ---------------------------------------------------------------------------

class TestCourseFacultyPermissionsAndFeatures:
    def test_view_attendance_and_crosscheck_presence(self, client):
        admin_tok = _make_admin(client)
        div1_id, _, c1_id, _, _, room_id, slot_id = _setup_env()

        tok_fac, id_fac = _make_user(client, admin_tok, "Prof Turing", "turing@campus.edu", "course_faculty")
        tok_stu, id_stu = _make_user(client, admin_tok, "Alice Student", "alice_fac@campus.edu", "student", division_id=div1_id)

        _db.session.add(FacultyCourseAssignment(faculty_id=id_fac, course_id=c1_id))
        _db.session.flush()

        today = date.today()
        presence = Presence(
            user_id=id_stu, room_id=room_id, slot_id=slot_id,
            presence_date=today, start_time=time(9, 0), end_time=time(10, 0)
        )
        _db.session.add(presence)
        _db.session.commit()

        headers = {"Authorization": f"Bearer {tok_fac}"}
        res = client.get(f"/api/faculty/courses/{c1_id}/attendance?date={today.isoformat()}", headers=headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["total_present"] == 1
        assert data["present_users"][0]["user_id"] == id_stu

    def test_health_summary_aggregate_counts_only_no_names_or_diagnoses(self, client):
        admin_tok = _make_admin(client)
        div1_id, _, c1_id, _, _, _, _ = _setup_env()

        tok_fac, id_fac = _make_user(client, admin_tok, "Prof Lovelace", "lovelace@campus.edu", "course_faculty")
        _, id_stu = _make_user(client, admin_tok, "Bob Student", "bob_fac@campus.edu", "student", division_id=div1_id)

        _db.session.add(FacultyCourseAssignment(faculty_id=id_fac, course_id=c1_id))
        _db.session.add(Enrollment(student_id=id_stu, course_id=c1_id))

        dkb = DiseaseKB(name="Covid-19", symptoms="fever, cough", preventive_measures="isolate")
        _db.session.add(dkb)
        _db.session.flush()

        # Student files health report with disease & custom symptoms
        hr = HealthRecord(user_id=id_stu, disease_id=dkb.id, custom_symptoms="Severe fever", onset_date=date.today(), severity="severe", status="reported")
        _db.session.add(hr)
        _db.session.commit()

        headers = {"Authorization": f"Bearer {tok_fac}"}
        res = client.get(f"/api/faculty/courses/{c1_id}/health-summary", headers=headers)
        assert res.status_code == 200
        data = res.get_json()

        # Check payload structure: COUNTS ONLY
        assert data["total_students"] >= 1
        assert data["under_observation"] == 1
        assert data["confirmed_cases"] == 0

        # Privacy verification: NO student names, NO user IDs, NO diagnosis names/symptoms
        json_str = res.get_data(as_text=True)
        assert "Bob" not in json_str
        assert "Covid" not in json_str
        assert "fever" not in json_str
        assert "custom_symptoms" not in json_str

    def test_flag_absence_no_diagnosis_field(self, client):
        admin_tok = _make_admin(client)
        div1_id, _, c1_id, _, _, _, _ = _setup_env()

        tok_fac, id_fac = _make_user(client, admin_tok, "Prof Hopper", "hopper@campus.edu", "course_faculty")
        _, id_stu = _make_user(client, admin_tok, "Charlie", "charlie_fac@campus.edu", "student", division_id=div1_id)

        _db.session.add(FacultyCourseAssignment(faculty_id=id_fac, course_id=c1_id))
        _db.session.commit()

        headers = {"Authorization": f"Bearer {tok_fac}"}
        res = client.post("/api/faculty/absence-flags", json={
            "student_id": id_stu,
            "course_id": c1_id,
            "flagged_date": date.today().isoformat(),
            "reason_category": "health_observed",
            "diagnosis": "Malaria",  # Extra diagnosis attempt
        }, headers=headers)
        assert res.status_code == 201
        data = res.get_json()
        assert "diagnosis" not in data
        assert data["reason_category"] == "health_observed"

        # View raised absence flags
        flags_res = client.get("/api/faculty/absence-flags", headers=headers)
        assert flags_res.status_code == 200
        flags = flags_res.get_json()
        assert len(flags) == 1
        assert flags[0]["student_id"] == id_stu

    def test_faculty_negative_tests(self, client):
        admin_tok = _make_admin(client)
        div1_id, _, c1_id, c2_id, _, _, _ = _setup_env()

        tok_fac_a, id_fac_a = _make_user(client, admin_tok, "Fac A", "fac_a_neg@campus.edu", "course_faculty")
        tok_fac_b, id_fac_b = _make_user(client, admin_tok, "Fac B", "fac_b_neg@campus.edu", "course_faculty")

        _db.session.add(FacultyCourseAssignment(faculty_id=id_fac_a, course_id=c1_id))
        _db.session.add(FacultyCourseAssignment(faculty_id=id_fac_b, course_id=c2_id))
        _db.session.commit()

        headers_a = {"Authorization": f"Bearer {tok_fac_a}"}

        # Cannot see another faculty's course data
        assert client.get(f"/api/faculty/courses/{c2_id}/attendance", headers=headers_a).status_code == 403
        assert client.get(f"/api/faculty/courses/{c2_id}/health-summary", headers=headers_a).status_code == 403

        # Cannot see full health records or student health endpoints
        assert client.get("/api/student/health-records", headers=headers_a).status_code == 403

        # Cannot access contact graph or admin dashboard routes
        assert client.get("/api/health-admin/contact-graph/1", headers=headers_a).status_code == 403
        assert client.get("/api/institute-admin/dashboards/aggregate", headers=headers_a).status_code == 403


# ---------------------------------------------------------------------------
# Test Cases — Class Teacher Routes & Permissions
# ---------------------------------------------------------------------------

class TestClassTeacherPermissionsAndFeatures:
    def test_class_teacher_division_pattern_and_escalations(self, client):
        admin_tok = _make_admin(client)
        div1_id, _, c1_id, c2_id, _, _, _ = _setup_env()

        tok_ct, id_ct = _make_user(client, admin_tok, "Class Teacher CT", "ct_perm@campus.edu", "class_teacher", division_id=div1_id)
        _, id_stu = _make_user(client, admin_tok, "Stu Division", "studiv@campus.edu", "student", division_id=div1_id)

        headers_ct = {"Authorization": f"Bearer {tok_ct}"}

        # Check division pattern
        res_pattern = client.get("/api/class-teacher/division-pattern", headers=headers_ct)
        assert res_pattern.status_code == 200
        pattern = res_pattern.get_json()
        assert pattern["division_id"] == div1_id
        assert len(pattern["courses"]) >= 2

        # Create absence flags across 2 distinct courses for the same student
        today = date.today()
        f1 = AbsenceFlag(student_id=id_stu, course_id=c1_id, faculty_id=id_ct, flagged_date=today, reason_category="health_observed")
        f2 = AbsenceFlag(student_id=id_stu, course_id=c2_id, faculty_id=id_ct, flagged_date=today, reason_category="health_observed")
        _db.session.add_all([f1, f2])
        _db.session.commit()

        # Check escalations endpoint (rolling window 14 days)
        res_esc = client.get("/api/class-teacher/escalations", headers=headers_ct)
        assert res_esc.status_code == 200
        esc_data = res_esc.get_json()
        assert esc_data["rolling_window_days"] == 14
        assert len(esc_data["escalations"]) == 1
        assert esc_data["escalations"][0]["student_id"] == id_stu

    def test_class_teacher_approve_enrollment_change(self, client):
        admin_tok = _make_admin(client)
        div1_id, c1_id, _, _, _, _, _ = _setup_env()

        tok_ct, id_ct = _make_user(client, admin_tok, "Class Teacher CT2", "ct_approve@campus.edu", "class_teacher", division_id=div1_id)
        _, id_stu = _make_user(client, admin_tok, "Stu Enrollment", "stuenr@campus.edu", "student", division_id=div1_id)

        en = Enrollment(student_id=id_stu, course_id=c1_id)
        _db.session.add(en)
        _db.session.commit()

        headers_ct = {"Authorization": f"Bearer {tok_ct}"}
        res = client.post(f"/api/class-teacher/enrollment-changes/{en.id}/approve", headers=headers_ct)
        assert res.status_code == 200
        assert res.get_json()["status"] == "approved"

    def test_class_teacher_approve_creates_queryable_enrollment_row(self, client):
        admin_tok = _make_admin(client)
        div1_id, _, c1_id, _, c_other_id, _, _ = _setup_env()

        tok_ct, id_ct = _make_user(client, admin_tok, "CT Elective Approver", "ct_elec@campus.edu", "class_teacher", division_id=div1_id)
        _, id_stu = _make_user(client, admin_tok, "Elective Student", "stu_elec@campus.edu", "student", division_id=div1_id)

        headers_ct = {"Authorization": f"Bearer {tok_ct}"}

        # Approve enrollment for cross-division elective course c_other_id
        res = client.post("/api/class-teacher/enrollment-changes/approve", headers=headers_ct, json={
            "student_id": id_stu,
            "course_id": c_other_id,
        })
        assert res.status_code in (200, 201)
        body = res.get_json()
        assert body["status"] == "approved"

        # Verify that an Enrollment row genuinely exists in the database!
        db_row = Enrollment.query.filter_by(student_id=id_stu, course_id=c_other_id).first()
        assert db_row is not None, "Approving enrollment change must genuinely create a queryable Enrollment row in the database"
        assert db_row.id == body["enrollment_id"]

    def test_class_teacher_negative_tests(self, client):
        admin_tok = _make_admin(client)
        div1_id, div2_id, c1_id, _, c_other_id, _, _ = _setup_env()

        tok_ct, id_ct = _make_user(client, admin_tok, "CT Division 1", "ct_div1@campus.edu", "class_teacher", division_id=div1_id)
        _, id_stu_div2 = _make_user(client, admin_tok, "Stu Division 2", "stu_div2@campus.edu", "student", division_id=div2_id)

        headers_ct = {"Authorization": f"Bearer {tok_ct}"}

        # Cannot see Division 2 data
        res_other = client.get(f"/api/class-teacher/division-pattern?division_id={div2_id}", headers=headers_ct)
        assert res_other.status_code == 403

        # Cannot approve enrollment for student in another division (Division 2)
        res_cross_div = client.post("/api/class-teacher/enrollment-changes/approve", headers=headers_ct, json={
            "student_id": id_stu_div2,
            "course_id": c1_id,
        })
        assert res_cross_div.status_code == 403
        assert "belong to your assigned division" in res_cross_div.get_json()["error"]

        # Cannot access system-wide configuration or Disease KB
        assert client.get("/api/institute-admin/system-config", headers=headers_ct).status_code == 403
        assert client.get("/api/health-admin/disease-kb", headers=headers_ct).status_code == 403

