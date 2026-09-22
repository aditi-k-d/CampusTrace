"""
End-to-End Integration Walkthrough Test
Scenario from Methodology.md:
Student reports illness -> Contact gets exposure alert -> Admin sees it on dashboard
"""

from datetime import date, time
import pytest

from app.extensions import db as _db
from app.models.division import Division, Room
from app.models.course import Course, Batch
from app.models.enrollment import Enrollment
from app.models.timetable import TimetableSlot
from app.models.presence import Presence
from app.models.health_record import HealthRecord
from app.models.alert import Alert
from app.models.user import User


def _make_admin(client):
    client.post("/api/auth/register", json={
        "name": "Institute Admin", "email": "admin_e2e@campus.edu",
        "password": "adminpassword", "role": "institute_admin",
    })
    resp = client.post("/api/auth/login", json={
        "email": "admin_e2e@campus.edu", "password": "adminpassword",
    })
    return resp.get_json()["access_token"]


def _make_health_admin(client, admin_tok):
    client.post("/api/auth/register", json={
        "name": "Health Admin", "email": "ha_e2e@campus.edu",
        "password": "hapassword", "role": "health_admin",
    }, headers={"Authorization": f"Bearer {admin_tok}"})
    resp = client.post("/api/auth/login", json={
        "email": "ha_e2e@campus.edu", "password": "hapassword",
    })
    return resp.get_json()["access_token"]


def _make_student(client, name, email, division_id=1):
    client.post("/api/auth/register", json={
        "name": name, "email": email,
        "password": "stupassword", "role": "student",
        "division_id": division_id,
    })
    resp = client.post("/api/auth/login", json={
        "email": email, "password": "stupassword",
    })
    data = resp.get_json()
    return data["access_token"], data["user"]["id"]


def test_end_to_end_methodology_scenario(client, app):
    # Setup Admin, Health Admin, Students
    admin_tok = _make_admin(client)
    ha_tok = _make_health_admin(client, admin_tok)

    div = Division(name="CS-C", branch="CS", year=2)
    room = Room(name="LH 101", building="Main Block", capacity=100)
    _db.session.add_all([div, room])
    _db.session.flush()

    course = Course(division_id=div.id, code="CS201", name="DSA", course_type="theory")
    _db.session.add(course)
    _db.session.flush()

    tok_s1, s1_id = _make_student(client, "Student One", "stu1_e2e@campus.edu", div.id)
    tok_s2, s2_id = _make_student(client, "Student Two", "stu2_e2e@campus.edu", div.id)

    slot = TimetableSlot(
        course_id=course.id, room_id=room.id, day_of_week=0,
        start_time=time(9, 0), end_time=time(10, 0)
    )
    _db.session.add(slot)
    _db.session.flush()

    # Simulate shared presence (contact event) on onset date
    onset_date = date(2026, 9, 14)
    p1 = Presence(user_id=s1_id, room_id=room.id, slot_id=slot.id, presence_date=onset_date, start_time=time(9, 0), end_time=time(10, 0))
    p2 = Presence(user_id=s2_id, room_id=room.id, slot_id=slot.id, presence_date=onset_date, start_time=time(9, 0), end_time=time(10, 0))
    _db.session.add_all([p1, p2])

    # ContactEdge created between s1 and s2
    from app.models.contact_edge import ContactEdge
    edge = ContactEdge(user_a_id=min(s1_id, s2_id), user_b_id=max(s1_id, s2_id), room_id=room.id, contact_date=onset_date, duration_minutes=60, room_type_weight=1.0)
    _db.session.add(edge)
    _db.session.commit()

    # Step A: Student 1 reports illness via POST /api/student/health-report
    rep_res = client.post("/api/student/health-report", json={
        "custom_symptoms": "High fever, persistent cough",
        "onset_date": "2026-09-14",
        "severity": "severe",
    }, headers={"Authorization": f"Bearer {tok_s1}"})
    assert rep_res.status_code == 201
    rep_data = rep_res.get_json()
    case_id = rep_data["id"]

    # Step B: Contact (Student 2) gets exposure alert via GET /api/student/alerts
    alerts_res = client.get("/api/student/alerts", headers={"Authorization": f"Bearer {tok_s2}"})
    assert alerts_res.status_code == 200
    alerts = alerts_res.get_json()
    assert len(alerts) >= 1
    assert alerts[0]["symptoms"] == "High fever, persistent cough"

    # Step C: Health Admin sees reported case & contact graph on dashboard
    cases_res = client.get("/api/health-admin/cases", headers={"Authorization": f"Bearer {ha_tok}"})
    assert cases_res.status_code == 200
    cases_list = cases_res.get_json()["items"]
    assert any(c["id"] == case_id for c in cases_list)

    graph_res = client.get(f"/api/health-admin/contact-graph/{case_id}", headers={"Authorization": f"Bearer {ha_tok}"})
    assert graph_res.status_code == 200
    graph_data = graph_res.get_json()
    assert str(s2_id) in graph_data["contacts"]["forward"] or s2_id in graph_data["contacts"]["forward"]

    # Step D: Institute Admin sees aggregate dashboard & audit logs
    agg_res = client.get("/api/institute-admin/dashboards/aggregate", headers={"Authorization": f"Bearer {admin_tok}"})
    assert agg_res.status_code == 200
    assert "divisions" in agg_res.get_json()

    audit_res = client.get("/api/institute-admin/audit-log", headers={"Authorization": f"Bearer {admin_tok}"})
    assert audit_res.status_code == 200
    assert "items" in audit_res.get_json()
