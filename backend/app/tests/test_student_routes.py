"""
Tests for app/routes/student.py.
Run: cd backend && pytest app/tests/test_student_routes.py -v
"""

from datetime import date
import pytest

from app.extensions import db as _db
from app.models.division import Division, Room
from app.models.course import Course, Batch
from app.models.enrollment import Enrollment
from app.models.health_record import HealthRecord
from app.models.alert import Alert
from app.models.absence_flag import AbsenceFlag
from app.models.feedback import Feedback
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


def _make_student(client, email="stu1@campus.edu", division_id=1):
    client.post("/api/auth/register", json={
        "name": f"Student {email}", "email": email,
        "password": "stupassword", "role": "student",
        "division_id": division_id,
    })
    resp = client.post("/api/auth/login", json={
        "email": email, "password": "stupassword",
    })
    data = resp.get_json()
    return data["access_token"], data["user"]["id"]


def _setup_division_and_courses():
    div = Division(name="CS-C", branch="CS", year=2)
    _db.session.add(div)
    _db.session.flush()

    c_theory = Course(division_id=div.id, code="CS201", name="DSA", course_type="theory")
    c_lab = Course(division_id=div.id, code="CS202L", name="DSA Lab", course_type="lab")
    c_tut = Course(division_id=div.id, code="CS203T", name="Math Tut", course_type="tutorial")
    _db.session.add_all([c_theory, c_lab, c_tut])
    _db.session.flush()

    b1 = Batch(course_id=c_lab.id, name="Batch C1")
    b2 = Batch(course_id=c_lab.id, name="Batch C2")
    bt1 = Batch(course_id=c_tut.id, name="Batch T1")
    _db.session.add_all([b1, b2, bt1])

    dkb = DiseaseKB(
        name="Flu",
        symptoms="fever, cough, fatigue, headache",
        preventive_measures="Rest, drink fluids, isolate for 5 days.",
        incubation_period_days=3,
    )
    _db.session.add(dkb)
    _db.session.commit()

    return div.id, c_theory.id, c_lab.id, c_tut.id, b1.id, b2.id, bt1.id, dkb.id


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

class TestRoleProtectionAndNegativeTests:
    def test_no_token_gets_401(self, client):
        assert client.get("/api/student/courses").status_code == 401
        assert client.post("/api/student/register-batches", json={}).status_code == 401

    def test_non_student_role_gets_403(self, client):
        admin_token = _make_admin(client)
        headers = {"Authorization": f"Bearer {admin_token}"}
        res = client.get("/api/student/courses", headers=headers)
        assert res.status_code == 403

    def test_student_cannot_access_other_role_routes_403(self, client):
        div_id, _, _, _, _, _, _, _ = _setup_division_and_courses()
        token, _ = _make_student(client, email="stu_no_access@campus.edu", division_id=div_id)
        headers = {"Authorization": f"Bearer {token}"}

        # Check endpoints across all other roles
        assert client.get("/api/faculty/courses/1/attendance", headers=headers).status_code == 403
        assert client.get("/api/class-teacher/division-pattern", headers=headers).status_code == 403
        assert client.get("/api/health-admin/cases", headers=headers).status_code == 403
        assert client.get("/api/institute-admin/audit-log", headers=headers).status_code == 403

    def test_student_cannot_fetch_other_student_data_via_param_manipulation(self, client):
        div_id, _, _, _, _, _, _, _ = _setup_division_and_courses()
        tok_a, id_a = _make_student(client, email="student_a@campus.edu", division_id=div_id)
        tok_b, id_b = _make_student(client, email="student_b@campus.edu", division_id=div_id)

        # Alice files health report
        hr = HealthRecord(user_id=id_a, onset_date=date(2026, 9, 10), severity="moderate", custom_symptoms="cough")
        _db.session.add(hr)
        _db.session.commit()

        # Bob tries to fetch courses/alerts/health-records passing Alice's student_id in query params
        res_courses = client.get(f"/api/student/courses?student_id={id_a}", headers={"Authorization": f"Bearer {tok_b}"})
        assert res_courses.status_code == 200
        # Bob only gets Bob's courses, not Alice's

        res_records = client.get(f"/api/student/health-records?student_id={id_a}", headers={"Authorization": f"Bearer {tok_b}"})
        assert res_records.status_code == 200
        assert len(res_records.get_json()) == 0  # Bob has 0 health records

    def test_no_room_or_cluster_level_aggregates_in_student_responses(self, client):
        div_id, _, _, _, _, _, _, _ = _setup_division_and_courses()
        token, _ = _make_student(client, email="stu_aggregates@campus.edu", division_id=div_id)
        headers = {"Authorization": f"Bearer {token}"}

        res_courses = client.get("/api/student/courses", headers=headers).get_json()
        for c in res_courses:
            assert "room_occupancy" not in c
            assert "cluster_count" not in c

        res_alerts = client.get("/api/student/alerts", headers=headers).get_json()
        for a in res_alerts:
            assert "room_id" not in a
            assert "cluster_id" not in a
            assert "building" not in a


class TestRegisterBatches:
    def test_success_lab_and_tutorial_batches(self, client):
        div_id, c_theory_id, c_lab_id, c_tut_id, b1_id, b2_id, bt1_id, _ = _setup_division_and_courses()
        token, _ = _make_student(client, email="stu_batches@campus.edu", division_id=div_id)
        headers = {"Authorization": f"Bearer {token}"}

        res = client.post("/api/student/register-batches", json={
            "batch_selections": [
                {"course_id": c_lab_id, "batch_id": b1_id},
                {"course_id": c_tut_id, "batch_id": bt1_id},
            ]
        }, headers=headers)
        assert res.status_code == 201
        data = res.get_json()
        assert len(data) == 2

    def test_theory_courses_need_no_batch_selection(self, client):
        div_id, c_theory_id, c_lab_id, c_tut_id, b1_id, _, _, _ = _setup_division_and_courses()
        token, _ = _make_student(client, email="stu_theory_nobatch@campus.edu", division_id=div_id)
        headers = {"Authorization": f"Bearer {token}"}

        # Select batch for lab only
        res = client.post("/api/student/register-batches", json={
            "batch_selections": [{"course_id": c_lab_id, "batch_id": b1_id}]
        }, headers=headers)
        assert res.status_code == 201

        # Check get/courses — theory course is included via division even without explicit batch selection
        courses = client.get("/api/student/courses", headers=headers).get_json()
        theory_course = next((c for c in courses if c["course_id"] == c_theory_id), None)
        assert theory_course is not None
        assert theory_course["batch_id"] is None


class TestHealthReportAndHistory:
    def test_report_via_disease_id_and_custom_symptoms(self, client):
        div_id, _, _, _, _, _, _, dkb_id = _setup_division_and_courses()
        token, _ = _make_student(client, email="stu_health@campus.edu", division_id=div_id)
        headers = {"Authorization": f"Bearer {token}"}

        # Report via disease_id
        res1 = client.post("/api/student/health-report", json={
            "disease_id": dkb_id,
            "onset_date": "2026-09-10",
            "severity": "moderate",
        }, headers=headers)
        assert res1.status_code == 201

        # Report via custom_symptoms
        res2 = client.post("/api/student/health-report", json={
            "custom_symptoms": "High fever and fatigue",
            "onset_date": "2026-09-12",
            "severity": "severe",
        }, headers=headers)
        assert res2.status_code == 201

        # Verify own health history endpoint
        history = client.get("/api/student/health-records", headers=headers).get_json()
        assert len(history) == 2
        assert history[0]["severity"] == "severe"

    def test_health_history_isolation(self, client):
        div_id, _, _, _, _, _, _, dkb_id = _setup_division_and_courses()
        tok_a, _ = _make_student(client, email="alice_hist@campus.edu", division_id=div_id)
        tok_b, _ = _make_student(client, email="bob_hist@campus.edu", division_id=div_id)

        client.post("/api/student/health-report", json={
            "disease_id": dkb_id,
            "onset_date": "2026-09-10",
            "severity": "mild",
        }, headers={"Authorization": f"Bearer {tok_a}"})

        # Alice sees her history
        hist_a = client.get("/api/student/health-records", headers={"Authorization": f"Bearer {tok_a}"}).get_json()
        assert len(hist_a) == 1

        # Bob sees empty history
        hist_b = client.get("/api/student/health-records", headers={"Authorization": f"Bearer {tok_b}"}).get_json()
        assert len(hist_b) == 0


class TestAlertPayloadAndPrivacy:
    def test_alert_payload_fields_and_privacy_guarantee(self, client):
        div_id, _, _, _, _, _, _, _ = _setup_division_and_courses()
        tok_a, id_a = _make_student(client, email="alice_alert@campus.edu", division_id=div_id)
        tok_b, id_b = _make_student(client, email="bob_alert@campus.edu", division_id=div_id)

        hr = HealthRecord(user_id=id_a, onset_date=date(2026, 9, 10), severity="mild")
        _db.session.add(hr)
        _db.session.flush()

        alert_b = Alert(
            user_id=id_b,
            source_health_record_id=hr.id,
            risk_level="medium",
            risk_score=0.65,
            symptoms_snapshot="fever, cough",
            precautions_snapshot="Isolate and monitor temperature.",
        )
        _db.session.add(alert_b)
        _db.session.commit()

        res_b = client.get("/api/student/alerts", headers={"Authorization": f"Bearer {tok_b}"})
        assert res_b.status_code == 200
        alerts = res_b.get_json()
        assert len(alerts) == 1
        alert = alerts[0]

        # Payload must include risk level, symptoms, preventive measures, recommended action
        assert alert["risk_level"] == "medium"
        assert alert["risk_score"] == 0.65
        assert alert["symptoms"] == "fever, cough"
        assert alert["precautions"] == "Isolate and monitor temperature."
        assert alert["preventive_measures"] == "Isolate and monitor temperature."
        assert alert["recommended_action"] == "Isolate and monitor temperature."

        # Payload MUST NOT include who exposed them!
        assert "source_user_id" not in alert
        assert "source_health_record_id" not in alert
        assert "index_case_name" not in alert
        assert "exposed_by" not in alert
        assert "contact_id" not in alert

    def test_alert_actions_acknowledge_and_false_positive_feedback(self, client):
        div_id, _, _, _, _, _, _, _ = _setup_division_and_courses()
        tok_b, id_b = _make_student(client, email="bob_actions@campus.edu", division_id=div_id)

        hr = HealthRecord(user_id=999, onset_date=date(2026, 9, 10), severity="mild")
        _db.session.add(hr)
        _db.session.flush()

        alert_b = Alert(
            user_id=id_b,
            source_health_record_id=hr.id,
            risk_level="high",
            risk_score=0.90,
            symptoms_snapshot="fever",
            precautions_snapshot="isolate",
        )
        _db.session.add(alert_b)
        _db.session.commit()

        # Acknowledge
        ack_res = client.post(f"/api/student/alerts/{alert_b.id}/acknowledge", headers={"Authorization": f"Bearer {tok_b}"})
        assert ack_res.status_code == 200

        # False positive flag creates Feedback row
        fp_res = client.post(f"/api/student/alerts/{alert_b.id}/false-positive", headers={"Authorization": f"Bearer {tok_b}"})
        assert fp_res.status_code == 201

        fb_row = Feedback.query.filter_by(alert_id=alert_b.id).first()
        assert fb_row is not None
        assert fb_row.is_false_positive is True


class TestAbsenceFlagsConfirmAndDeny:
    def test_confirm_and_deny_absence_flags(self, client):
        div_id, c_theory_id, _, _, _, _, _, _ = _setup_division_and_courses()
        tok_a, id_a = _make_student(client, email="abs_confirm@campus.edu", division_id=div_id)
        tok_b, id_b = _make_student(client, email="abs_deny@campus.edu", division_id=div_id)

        flag_a = AbsenceFlag(student_id=id_a, course_id=c_theory_id, faculty_id=1, flagged_date=date(2026, 9, 12), reason_category="health_observed", state="pending")
        flag_b = AbsenceFlag(student_id=id_b, course_id=c_theory_id, faculty_id=1, flagged_date=date(2026, 9, 12), reason_category="health_observed", state="pending")
        _db.session.add_all([flag_a, flag_b])
        _db.session.commit()

        # Student A confirms
        res_a = client.post(f"/api/student/absence-flags/{flag_a.id}/respond", json={"confirm": True}, headers={"Authorization": f"Bearer {tok_a}"})
        assert res_a.status_code == 200
        assert res_a.get_json()["state"] == "confirmed"

        # Student B denies
        res_b = client.post(f"/api/student/absence-flags/{flag_b.id}/respond", json={"confirm": False}, headers={"Authorization": f"Bearer {tok_b}"})
        assert res_b.status_code == 200
        assert res_b.get_json()["state"] == "dismissed"


class TestSelfAssessmentTool:
    def test_self_assessment_runs_independently(self, client):
        div_id, _, _, _, _, _, _, _ = _setup_division_and_courses()
        tok, _ = _make_student(client, email="self_assess_alone@campus.edu", division_id=div_id)

        # Student has NO filed health report
        records = client.get("/api/student/health-records", headers={"Authorization": f"Bearer {tok}"}).get_json()
        assert len(records) == 0

        # Self-assessment still works cleanly
        res = client.post("/api/student/self-assessment", json={
            "symptoms": ["fever", "cough", "headache"]
        }, headers={"Authorization": f"Bearer {tok}"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["matched_disease"] == "Flu"
        assert "recommended_action" in data
