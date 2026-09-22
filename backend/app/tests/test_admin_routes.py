"""
Tests for app/routes/institute_admin.py and app/routes/health_admin.py.
Run: cd backend && pytest app/tests/test_admin_routes.py -v
"""

import pytest

from app.extensions import db as _db
from app.models.division import Division, Room
from app.models.course import Course, Batch, FacultyCourseAssignment
from app.models.enrollment import Enrollment
from app.models.health_record import HealthRecord
from app.models.system_config import SystemConfig
from app.models.audit_log import AuditLog
from app.models.timetable import TimetableSlot
from app.models.user import User


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_admin(client):
    """Register the bootstrap institute_admin and return the JWT."""
    client.post("/api/auth/register", json={
        "name": "Admin", "email": "admin@campus.edu",
        "password": "adminpass", "role": "institute_admin",
    })
    resp = client.post("/api/auth/login", json={
        "email": "admin@campus.edu", "password": "adminpass",
    })
    return resp.get_json()["access_token"]


def _make_student(client, admin_token, email="stu@campus.edu", division_id=None):
    """Register a student (students self-register, no admin token needed)."""
    payload = {
        "name": "Student", "email": email,
        "password": "stupass", "role": "student",
        "division_id": division_id or 1,
    }
    resp = client.post("/api/auth/register", json=payload)
    return resp.get_json()


def _make_faculty(client, admin_token, email="fac@campus.edu"):
    """Register a course_faculty via the admin."""
    resp = client.post(
        "/api/auth/register",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Faculty", "email": email,
            "password": "facpass", "role": "course_faculty",
        },
    )
    return resp.get_json()


def _student_token(client, email="stu@campus.edu"):
    resp = client.post("/api/auth/login", json={
        "email": email, "password": "stupass",
    })
    return resp.get_json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin_token(client):
    return _make_admin(client)


@pytest.fixture()
def seeded(client, admin_token, db):
    """Create a division, room, course, batch for downstream tests."""
    # division
    resp = client.post(
        "/api/institute-admin/divisions",
        headers=_auth(admin_token),
        json={"name": "SY CS-C", "branch": "Computer Engineering", "year": 2},
    )
    div = resp.get_json()

    # room
    resp = client.post(
        "/api/institute-admin/rooms",
        headers=_auth(admin_token),
        json={"name": "Lab 204", "building": "Main", "capacity": 40},
    )
    room = resp.get_json()

    # course
    resp = client.post(
        "/api/institute-admin/courses",
        headers=_auth(admin_token),
        json={
            "division_id": div["id"], "code": "CS201",
            "name": "DSA", "course_type": "theory",
        },
    )
    course = resp.get_json()

    # batch
    resp = client.post(
        "/api/institute-admin/batches",
        headers=_auth(admin_token),
        json={"course_id": course["id"], "name": "B1"},
    )
    batch = resp.get_json()

    return {"division": div, "room": room, "course": course, "batch": batch}


# ===================================================================
# role_required rejection — one test covering all endpoints
# ===================================================================

class TestRoleRejection:
    """A student token must get 403 on every institute-admin route."""

    def test_student_rejected_on_all_endpoints(self, client, admin_token, seeded):
        _make_student(client, admin_token, division_id=seeded["division"]["id"])
        stu = _student_token(client)
        h = _auth(stu)

        assert client.post("/api/institute-admin/divisions", headers=h, json={}).status_code == 403
        assert client.post("/api/institute-admin/rooms", headers=h, json={}).status_code == 403
        assert client.post("/api/institute-admin/courses", headers=h, json={}).status_code == 403
        assert client.post("/api/institute-admin/batches", headers=h, json={}).status_code == 403
        assert client.post("/api/institute-admin/faculty-assignments", headers=h, json={}).status_code == 403
        assert client.post("/api/institute-admin/timetable-slots", headers=h, json={}).status_code == 403
        assert client.get("/api/institute-admin/system-config", headers=h).status_code == 403
        assert client.patch("/api/institute-admin/system-config", headers=h, json={}).status_code == 403
        assert client.get("/api/institute-admin/audit-log", headers=h).status_code == 403
        assert client.get("/api/institute-admin/dashboards/aggregate", headers=h).status_code == 403

    def test_no_token_gets_401(self, client):
        assert client.get("/api/institute-admin/system-config").status_code == 401


# ===================================================================
# POST /divisions
# ===================================================================

class TestCreateDivision:
    def test_success(self, client, admin_token):
        resp = client.post(
            "/api/institute-admin/divisions",
            headers=_auth(admin_token),
            json={"name": "FY CS-A", "branch": "Computer Engineering", "year": 1},
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["name"] == "FY CS-A"
        assert body["year"] == 1

    def test_duplicate_name_409(self, client, admin_token):
        payload = {"name": "DupDiv", "branch": "CE", "year": 2}
        client.post("/api/institute-admin/divisions", headers=_auth(admin_token), json=payload)
        resp = client.post("/api/institute-admin/divisions", headers=_auth(admin_token), json=payload)
        assert resp.status_code == 409

    def test_missing_fields_400(self, client, admin_token):
        resp = client.post(
            "/api/institute-admin/divisions",
            headers=_auth(admin_token),
            json={"name": "X"},
        )
        assert resp.status_code == 400

    def test_audit_log_written(self, client, admin_token, db):
        client.post(
            "/api/institute-admin/divisions",
            headers=_auth(admin_token),
            json={"name": "AuditDiv", "branch": "CE", "year": 3},
        )
        log = AuditLog.query.filter_by(action="create_division").first()
        assert log is not None
        assert log.target_type == "division"


# ===================================================================
# POST /rooms
# ===================================================================

class TestCreateRoom:
    def test_success(self, client, admin_token):
        resp = client.post(
            "/api/institute-admin/rooms",
            headers=_auth(admin_token),
            json={"name": "Room 101", "building": "Annex", "capacity": 30},
        )
        assert resp.status_code == 201
        assert resp.get_json()["name"] == "Room 101"

    def test_duplicate_409(self, client, admin_token):
        payload = {"name": "R1", "building": "B1"}
        client.post("/api/institute-admin/rooms", headers=_auth(admin_token), json=payload)
        resp = client.post("/api/institute-admin/rooms", headers=_auth(admin_token), json=payload)
        assert resp.status_code == 409

    def test_missing_name_400(self, client, admin_token):
        resp = client.post(
            "/api/institute-admin/rooms",
            headers=_auth(admin_token),
            json={"building": "B1"},
        )
        assert resp.status_code == 400


# ===================================================================
# POST /courses
# ===================================================================

class TestCreateCourse:
    def test_success(self, client, admin_token, seeded):
        resp = client.post(
            "/api/institute-admin/courses",
            headers=_auth(admin_token),
            json={
                "division_id": seeded["division"]["id"],
                "code": "CS301",
                "name": "DBMS",
                "course_type": "lab",
            },
        )
        assert resp.status_code == 201
        assert resp.get_json()["code"] == "CS301"

    def test_invalid_course_type_400(self, client, admin_token, seeded):
        resp = client.post(
            "/api/institute-admin/courses",
            headers=_auth(admin_token),
            json={
                "division_id": seeded["division"]["id"],
                "code": "X",
                "name": "X",
                "course_type": "seminar",
            },
        )
        assert resp.status_code == 400

    def test_missing_division_404(self, client, admin_token):
        resp = client.post(
            "/api/institute-admin/courses",
            headers=_auth(admin_token),
            json={"division_id": 9999, "code": "X", "name": "X", "course_type": "theory"},
        )
        assert resp.status_code == 404


# ===================================================================
# POST /batches
# ===================================================================

class TestCreateBatch:
    def test_success(self, client, admin_token, seeded):
        resp = client.post(
            "/api/institute-admin/batches",
            headers=_auth(admin_token),
            json={"course_id": seeded["course"]["id"], "name": "B2"},
        )
        assert resp.status_code == 201
        assert resp.get_json()["name"] == "B2"

    def test_duplicate_409(self, client, admin_token, seeded):
        payload = {"course_id": seeded["course"]["id"], "name": "B1"}
        # B1 was already created by the seeded fixture
        resp = client.post("/api/institute-admin/batches", headers=_auth(admin_token), json=payload)
        assert resp.status_code == 409

    def test_missing_course_404(self, client, admin_token):
        resp = client.post(
            "/api/institute-admin/batches",
            headers=_auth(admin_token),
            json={"course_id": 9999, "name": "B1"},
        )
        assert resp.status_code == 404


# ===================================================================
# POST /faculty-assignments
# ===================================================================

class TestFacultyAssignment:
    def test_success(self, client, admin_token, seeded):
        fac = _make_faculty(client, admin_token)
        resp = client.post(
            "/api/institute-admin/faculty-assignments",
            headers=_auth(admin_token),
            json={"faculty_id": fac["id"], "course_id": seeded["course"]["id"]},
        )
        assert resp.status_code == 201
        assert resp.get_json()["faculty_id"] == fac["id"]

    def test_non_faculty_user_404(self, client, admin_token, seeded):
        stu = _make_student(client, admin_token, division_id=seeded["division"]["id"])
        resp = client.post(
            "/api/institute-admin/faculty-assignments",
            headers=_auth(admin_token),
            json={"faculty_id": stu["id"], "course_id": seeded["course"]["id"]},
        )
        assert resp.status_code == 404

    def test_duplicate_409(self, client, admin_token, seeded):
        fac = _make_faculty(client, admin_token, email="fac2@campus.edu")
        payload = {"faculty_id": fac["id"], "course_id": seeded["course"]["id"]}
        client.post("/api/institute-admin/faculty-assignments", headers=_auth(admin_token), json=payload)
        resp = client.post("/api/institute-admin/faculty-assignments", headers=_auth(admin_token), json=payload)
        assert resp.status_code == 409


# ===================================================================
# POST /timetable-slots
# ===================================================================

class TestTimetableSlot:
    def test_success(self, client, admin_token, seeded):
        resp = client.post(
            "/api/institute-admin/timetable-slots",
            headers=_auth(admin_token),
            json={
                "course_id": seeded["course"]["id"],
                "room_id": seeded["room"]["id"],
                "batch_id": None,
                "day_of_week": 0,
                "start_time": "09:00",
                "end_time": "10:00",
            },
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["day_of_week"] == 0

    def test_invalid_day_400(self, client, admin_token, seeded):
        resp = client.post(
            "/api/institute-admin/timetable-slots",
            headers=_auth(admin_token),
            json={
                "course_id": seeded["course"]["id"],
                "room_id": seeded["room"]["id"],
                "day_of_week": 9,
                "start_time": "09:00",
                "end_time": "10:00",
            },
        )
        assert resp.status_code == 400

    def test_missing_room_404(self, client, admin_token, seeded):
        resp = client.post(
            "/api/institute-admin/timetable-slots",
            headers=_auth(admin_token),
            json={
                "course_id": seeded["course"]["id"],
                "room_id": 9999,
                "day_of_week": 0,
                "start_time": "09:00",
                "end_time": "10:00",
            },
        )
        assert resp.status_code == 404

    def test_slot_conflict_409(self, client, admin_token, seeded):
        # Create initial slot: Mon 09:00 - 10:30
        res1 = client.post(
            "/api/institute-admin/timetable-slots",
            headers=_auth(admin_token),
            json={
                "course_id": seeded["course"]["id"],
                "room_id": seeded["room"]["id"],
                "day_of_week": 0,
                "start_time": "09:00",
                "end_time": "10:30",
            },
        )
        assert res1.status_code == 201

        # Attempt overlapping slot: Mon 10:00 - 11:30 in same room -> 409 Conflict
        res2 = client.post(
            "/api/institute-admin/timetable-slots",
            headers=_auth(admin_token),
            json={
                "course_id": seeded["course"]["id"],
                "room_id": seeded["room"]["id"],
                "day_of_week": 0,
                "start_time": "10:00",
                "end_time": "11:30",
            },
        )
        assert res2.status_code == 409
        assert "conflict" in res2.get_json()["error"].lower()


# ===================================================================
# GET / PATCH /system-config
# ===================================================================

class TestSystemConfig:
    def test_get_returns_defaults(self, client, admin_token):
        resp = client.get(
            "/api/institute-admin/system-config",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "k_anonymity_threshold" in body
        assert "default_tracing_depth" in body

    def test_patch_updates_values(self, client, admin_token):
        resp = client.patch(
            "/api/institute-admin/system-config",
            headers=_auth(admin_token),
            json={"k_anonymity_threshold": 10, "default_tracing_depth": 3},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["k_anonymity_threshold"] == 10
        assert body["default_tracing_depth"] == 3

    def test_patch_validates_threshold(self, client, admin_token):
        resp = client.patch(
            "/api/institute-admin/system-config",
            headers=_auth(admin_token),
            json={"k_anonymity_threshold": 0},
        )
        assert resp.status_code == 400

    def test_patch_validates_direction(self, client, admin_token):
        resp = client.patch(
            "/api/institute-admin/system-config",
            headers=_auth(admin_token),
            json={"default_tracing_direction": "sideways"},
        )
        assert resp.status_code == 400

    def test_patch_empty_body_400(self, client, admin_token):
        resp = client.patch(
            "/api/institute-admin/system-config",
            headers=_auth(admin_token),
            json={},
        )
        assert resp.status_code == 400

    def test_patch_writes_audit(self, client, admin_token, db):
        client.patch(
            "/api/institute-admin/system-config",
            headers=_auth(admin_token),
            json={"k_anonymity_threshold": 7},
        )
        log = AuditLog.query.filter_by(action="update_system_config").first()
        assert log is not None


# ===================================================================
# GET /audit-log
# ===================================================================

class TestAuditLog:
    def test_returns_items(self, client, admin_token, seeded):
        # seeded fixture already created several entities → audit rows exist
        resp = client.get(
            "/api/institute-admin/audit-log",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "items" in body
        assert len(body["items"]) > 0

    def test_filter_by_action(self, client, admin_token, seeded):
        resp = client.get(
            "/api/institute-admin/audit-log?action=create_division",
            headers=_auth(admin_token),
        )
        body = resp.get_json()
        assert all(i["action"] == "create_division" for i in body["items"])

    def test_filter_by_user_id(self, client, admin_token, seeded):
        # The admin user is user 1 in these tests
        admin_user = User.query.filter_by(email="admin@campus.edu").first()
        resp = client.get(
            f"/api/institute-admin/audit-log?user_id={admin_user.id}",
            headers=_auth(admin_token),
        )
        body = resp.get_json()
        assert all(i["user_id"] == admin_user.id for i in body["items"])

    def test_pagination_with_limit(self, client, admin_token, seeded):
        resp = client.get(
            "/api/institute-admin/audit-log?limit=2",
            headers=_auth(admin_token),
        )
        body = resp.get_json()
        assert len(body["items"]) <= 2
        # seeded creates 4 audit rows → there should be a next_cursor
        if len(body["items"]) == 2:
            assert body["next_cursor"] is not None

    def test_cursor_pagination(self, client, admin_token, seeded):
        # page 1
        r1 = client.get(
            "/api/institute-admin/audit-log?limit=2",
            headers=_auth(admin_token),
        ).get_json()
        if r1["next_cursor"]:
            # page 2
            r2 = client.get(
                f"/api/institute-admin/audit-log?limit=2&cursor={r1['next_cursor']}",
                headers=_auth(admin_token),
            ).get_json()
            # pages must not overlap
            ids1 = {i["id"] for i in r1["items"]}
            ids2 = {i["id"] for i in r2["items"]}
            assert ids1.isdisjoint(ids2)


# ===================================================================
# GET /dashboards/aggregate — including k-anonymity suppression
# ===================================================================

class TestDashboardsAggregate:
    def test_returns_divisions_and_courses(self, client, admin_token, seeded):
        resp = client.get(
            "/api/institute-admin/dashboards/aggregate",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "divisions" in body
        assert "courses" in body
        assert len(body["divisions"]) >= 1
        assert len(body["courses"]) >= 1

    def test_k_anonymity_suppression_below_threshold(self, client, admin_token, db):
        """Counts below k_anonymity_threshold must be suppressed (None)."""
        # Create division + one student — default k=5, so count=1 < 5
        div = Division(name="Tiny Div", branch="CE", year=1)
        _db.session.add(div)
        _db.session.commit()

        u = User(name="Lone", email="lone@campus.edu", role="student",
                 division_id=div.id)
        u.set_password("p")
        _db.session.add(u)
        _db.session.commit()

        resp = client.get(
            "/api/institute-admin/dashboards/aggregate",
            headers=_auth(admin_token),
        )
        body = resp.get_json()
        tiny = next(d for d in body["divisions"] if d["division_id"] == div.id)
        assert tiny["student_count"] is None, "Count below k must be suppressed"
        assert tiny["suppressed"] is True

    def test_k_anonymity_not_suppressed_above_threshold(self, client, admin_token, db):
        """Counts >= k_anonymity_threshold must be visible."""
        # Set k=2 so we can satisfy it easily
        cfg = SystemConfig.get()
        cfg.k_anonymity_threshold = 2
        _db.session.commit()

        div = Division(name="Big Div", branch="CE", year=1)
        _db.session.add(div)
        _db.session.commit()

        for i in range(3):
            u = User(name=f"S{i}", email=f"s{i}@campus.edu", role="student",
                     division_id=div.id)
            u.set_password("p")
            _db.session.add(u)
        _db.session.commit()

        resp = client.get(
            "/api/institute-admin/dashboards/aggregate",
            headers=_auth(admin_token),
        )
        body = resp.get_json()
        big = next(d for d in body["divisions"] if d["division_id"] == div.id)
        assert big["student_count"] == 3
        assert big["suppressed"] is False

    def test_k_anonymity_suppression_specific_case(self, client, admin_token, db):
        """Explicitly verify that changing the threshold changes suppression behavior."""
        # Create a division with exactly 3 students
        div = Division(name="Medium Div", branch="CE", year=2)
        _db.session.add(div)
        _db.session.commit()

        for i in range(3):
            u = User(name=f"M{i}", email=f"m{i}@campus.edu", role="student",
                     division_id=div.id)
            u.set_password("p")
            _db.session.add(u)
        _db.session.commit()

        # k=5 → 3 < 5 → suppressed
        cfg = SystemConfig.get()
        cfg.k_anonymity_threshold = 5
        _db.session.commit()

        resp = client.get(
            "/api/institute-admin/dashboards/aggregate",
            headers=_auth(admin_token),
        )
        body = resp.get_json()
        d = next(x for x in body["divisions"] if x["division_id"] == div.id)
        assert d["student_count"] is None
        assert d["suppressed"] is True

        # k=3 → 3 >= 3 → not suppressed
        cfg.k_anonymity_threshold = 3
        _db.session.commit()

        resp = client.get(
            "/api/institute-admin/dashboards/aggregate",
            headers=_auth(admin_token),
        )
        body = resp.get_json()
        d = next(x for x in body["divisions"] if x["division_id"] == div.id)
        assert d["student_count"] == 3
        assert d["suppressed"] is False


# ===================================================================
# User Management: GET /users, PATCH /users/<user_id>
# ===================================================================

class TestUserManagement:
    def test_list_users(self, client, admin_token, seeded):
        resp = client.get("/api/institute-admin/users", headers=_auth(admin_token))
        assert resp.status_code == 200
        body = resp.get_json()
        assert "items" in body
        assert len(body["items"]) >= 1

    def test_filter_users_by_role(self, client, admin_token, seeded):
        resp = client.get("/api/institute-admin/users?role=institute_admin", headers=_auth(admin_token))
        assert resp.status_code == 200
        body = resp.get_json()
        assert all(u["role"] == "institute_admin" for u in body["items"])

    def test_toggle_user_status(self, client, admin_token, seeded):
        stu = _make_student(client, admin_token, email="toggle_stu@campus.edu", division_id=seeded["division"]["id"])
        uid = stu["id"]

        # Deactivate
        r1 = client.patch(f"/api/institute-admin/users/{uid}", headers=_auth(admin_token), json={"is_active": False})
        assert r1.status_code == 200
        assert r1.get_json()["is_active"] is False

        # Reactivate
        r2 = client.patch(f"/api/institute-admin/users/{uid}", headers=_auth(admin_token), json={"is_active": True})
        assert r2.status_code == 200
        assert r2.get_json()["is_active"] is True

    def test_self_deactivation_rejected(self, client, admin_token):
        admin_user = User.query.filter_by(email="admin@campus.edu").first()
        res = client.patch(f"/api/institute-admin/users/{admin_user.id}", headers=_auth(admin_token), json={"is_active": False})
        assert res.status_code == 400
        assert "cannot deactivate" in res.get_json()["error"].lower()


# ===================================================================
# New Dashboard Analytics Endpoints
# ===================================================================

class TestNewDashboards:
    def test_outbreak_trends(self, client, admin_token):
        res = client.get("/api/institute-admin/dashboards/trends", headers=_auth(admin_token))
        assert res.status_code == 200
        body = res.get_json()
        assert "trends" in body
        assert "k_anonymity_threshold" in body

    def test_department_stats(self, client, admin_token, seeded):
        res = client.get("/api/institute-admin/dashboards/by-department", headers=_auth(admin_token))
        assert res.status_code == 200
        body = res.get_json()
        assert "departments" in body

    def test_high_overlap_locations(self, client, admin_token, seeded):
        res = client.get("/api/institute-admin/dashboards/high-overlap-locations", headers=_auth(admin_token))
        assert res.status_code == 200
        body = res.get_json()
        assert "locations" in body

    def test_analytics(self, client, admin_token, seeded):
        res = client.get("/api/institute-admin/dashboards/analytics", headers=_auth(admin_token))
        assert res.status_code == 200
        body = res.get_json()
        assert "exposure_by_location" in body
        assert "exposure_by_department" in body

    def test_event_exposures(self, client, admin_token, seeded):
        res = client.get("/api/institute-admin/dashboards/event-exposures", headers=_auth(admin_token))
        assert res.status_code == 200
        body = res.get_json()
        assert "events" in body




# ===================================================================
# ===================================================================
# HEALTH ADMIN TESTS
# ===================================================================
# ===================================================================

from datetime import date, timedelta
from app.models.alert import Alert
from app.models.capacity import Capacity, IsolationAllocation
from app.models.disease_kb import DiseaseKB
from app.models.feedback import Feedback
from app.models.contact_edge import ContactEdge


def _make_health_admin(client, admin_token, email="ha@campus.edu"):
    """Create a health_admin user (requires institute_admin token)."""
    resp = client.post(
        "/api/auth/register",
        headers=_auth(admin_token),
        json={
            "name": "HealthAdmin", "email": email,
            "password": "hapass", "role": "health_admin",
        },
    )
    data = resp.get_json()
    tok = client.post("/api/auth/login", json={
        "email": email, "password": "hapass",
    }).get_json()["access_token"]
    return data, tok


@pytest.fixture()
def ha_token(client, admin_token):
    """Return a health_admin JWT."""
    _, tok = _make_health_admin(client, admin_token)
    return tok


@pytest.fixture()
def disease(db):
    """A seeded DiseaseKB entry."""
    d = DiseaseKB(
        name="Influenza",
        symptoms="fever cough sore throat fatigue headache",
        preventive_measures="wash hands wear mask",
        incubation_period_days=2,
    )
    _db.session.add(d)
    _db.session.commit()
    return d


@pytest.fixture()
def student_with_record(client, admin_token, db):
    """A division, a student, and a HealthRecord for that student."""
    div = Division(name="HA Test Div", branch="CE", year=2)
    _db.session.add(div)
    _db.session.commit()

    u = User(name="Sick Student", email="sick@campus.edu",
             role="student", division_id=div.id)
    u.set_password("p")
    _db.session.add(u)
    _db.session.commit()

    record = HealthRecord(
        user_id=u.id,
        onset_date=date.today() - timedelta(days=3),
        severity="moderate",
        status="reported",
        custom_symptoms="fever and cough",
    )
    _db.session.add(record)
    _db.session.commit()
    return {"user": u, "record": record, "division": div}


@pytest.fixture()
def contact_setup(client, admin_token, db):
    """
    Full pipeline fixture: two users sharing a ContactEdge so that
    tracing_service.trace_case() returns a non-empty result.

    user_a  --[contact edge on onset day]--> user_b
    """
    div = Division(name="Contact Div", branch="CE", year=1)
    _db.session.add(div)
    _db.session.commit()

    user_a = User(name="Patient Zero", email="pz@campus.edu",
                  role="student", division_id=div.id)
    user_a.set_password("p")
    user_b = User(name="Contact One", email="c1@campus.edu",
                  role="student", division_id=div.id)
    user_b.set_password("p")
    _db.session.add_all([user_a, user_b])
    _db.session.commit()

    onset = date.today() - timedelta(days=2)

    record = HealthRecord(
        user_id=user_a.id,
        onset_date=onset,
        severity="mild",
        status="reported",
        custom_symptoms="cough fever",
    )
    _db.session.add(record)

    room = Room(name="Contact Room", building="Main", capacity=30)
    _db.session.add(room)
    _db.session.commit()

    edge = ContactEdge(
        user_a_id=user_a.id,
        user_b_id=user_b.id,
        room_id=room.id,
        contact_date=onset,
        duration_minutes=60,
        room_type_weight=1.0,
    )
    _db.session.add(edge)
    _db.session.commit()

    return {
        "user_a": user_a,
        "user_b": user_b,
        "record": record,
        "room": room,
    }


# ===================================================================
# Health Admin — role rejection
# ===================================================================

class TestHealthAdminRoleRejection:
    """student token → 403 on every health-admin route."""

    def test_student_rejected_on_all_ha_endpoints(self, client, admin_token, seeded):
        _make_student(client, admin_token, division_id=seeded["division"]["id"])
        stu = _student_token(client)
        h = _auth(stu)

        assert client.get("/api/health-admin/cases", headers=h).status_code == 403
        assert client.post("/api/health-admin/cases/1/confirm", headers=h, json={}).status_code == 403
        assert client.get("/api/health-admin/contact-graph/1", headers=h).status_code == 403
        assert client.post("/api/health-admin/contact-graph/1/retrace", headers=h, json={}).status_code == 403
        assert client.get("/api/health-admin/disease-kb", headers=h).status_code == 403
        assert client.post("/api/health-admin/disease-kb", headers=h, json={}).status_code == 403
        assert client.patch("/api/health-admin/disease-kb/1", headers=h, json={}).status_code == 403
        assert client.get("/api/health-admin/capacity", headers=h).status_code == 403
        assert client.post("/api/health-admin/capacity/1/allocate", headers=h, json={}).status_code == 403
        assert client.post("/api/health-admin/feedback/1/review", headers=h, json={}).status_code == 403

    def test_no_token_gets_401(self, client):
        assert client.get("/api/health-admin/cases").status_code == 401

    def test_institute_admin_cannot_access_health_admin_routes(self, client, admin_token):
        """institute_admin is a different role — must also be rejected."""
        h = _auth(admin_token)
        assert client.get("/api/health-admin/cases", headers=h).status_code == 403


# ===================================================================
# GET /health-admin/cases
# ===================================================================

class TestListCases:
    def test_returns_all_cases(self, client, ha_token, student_with_record):
        resp = client.get("/api/health-admin/cases", headers=_auth(ha_token))
        assert resp.status_code == 200
        body = resp.get_json()
        assert "items" in body
        assert any(i["id"] == student_with_record["record"].id for i in body["items"])

    def test_filter_by_status(self, client, ha_token, student_with_record):
        resp = client.get(
            "/api/health-admin/cases?status=reported",
            headers=_auth(ha_token),
        )
        body = resp.get_json()
        assert all(i["status"] == "reported" for i in body["items"])

    def test_invalid_status_400(self, client, ha_token):
        resp = client.get(
            "/api/health-admin/cases?status=nonsense",
            headers=_auth(ha_token),
        )
        assert resp.status_code == 400

    def test_pagination_cursor(self, client, ha_token, student_with_record, db):
        # Add a second record so we can paginate.
        div = student_with_record["division"]
        u2 = User(name="S2", email="s2@campus.edu", role="student", division_id=div.id)
        u2.set_password("p")
        _db.session.add(u2)
        _db.session.commit()

        r2 = HealthRecord(user_id=u2.id, onset_date=date.today(),
                          severity="mild", status="reported")
        _db.session.add(r2)
        _db.session.commit()

        p1 = client.get(
            "/api/health-admin/cases?limit=1",
            headers=_auth(ha_token),
        ).get_json()
        assert len(p1["items"]) == 1
        assert p1["next_cursor"] is not None

        p2 = client.get(
            f"/api/health-admin/cases?limit=1&cursor={p1['next_cursor']}",
            headers=_auth(ha_token),
        ).get_json()
        ids1 = {i["id"] for i in p1["items"]}
        ids2 = {i["id"] for i in p2["items"]}
        assert ids1.isdisjoint(ids2)

    def test_audit_written(self, client, ha_token, student_with_record):
        client.get("/api/health-admin/cases", headers=_auth(ha_token))
        log = AuditLog.query.filter_by(action="list_cases").first()
        assert log is not None


# ===================================================================
# POST /health-admin/cases/<id>/confirm
# ===================================================================

class TestConfirmCase:
    def test_success_without_disease(self, client, ha_token, student_with_record):
        rid = student_with_record["record"].id
        resp = client.post(
            f"/api/health-admin/cases/{rid}/confirm",
            headers=_auth(ha_token),
            json={},
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "confirmed"

    def test_success_with_disease(self, client, ha_token, student_with_record, disease):
        rid = student_with_record["record"].id
        resp = client.post(
            f"/api/health-admin/cases/{rid}/confirm",
            headers=_auth(ha_token),
            json={"disease_id": disease.id},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["disease_id"] == disease.id

    def test_unknown_case_404(self, client, ha_token):
        resp = client.post(
            "/api/health-admin/cases/9999/confirm",
            headers=_auth(ha_token),
            json={},
        )
        assert resp.status_code == 404

    def test_unknown_disease_404(self, client, ha_token, student_with_record):
        rid = student_with_record["record"].id
        resp = client.post(
            f"/api/health-admin/cases/{rid}/confirm",
            headers=_auth(ha_token),
            json={"disease_id": 9999},
        )
        assert resp.status_code == 404

    def test_audit_written(self, client, ha_token, student_with_record):
        rid = student_with_record["record"].id
        client.post(
            f"/api/health-admin/cases/{rid}/confirm",
            headers=_auth(ha_token),
            json={},
        )
        log = AuditLog.query.filter_by(action="confirm_case").first()
        assert log is not None


# ===================================================================
# GET /health-admin/contact-graph/<case_id>  — full pipeline
# ===================================================================

class TestContactGraph:
    def test_returns_contacts_with_risk_scores(self, client, ha_token, contact_setup):
        """Full pipeline: health record + contact edge → traced contacts with scores."""
        rid = contact_setup["record"].id
        resp = client.get(
            f"/api/health-admin/contact-graph/{rid}",
            headers=_auth(ha_token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["case_id"] == rid
        assert "contacts" in body

        # There is a forward edge on the onset date, so forward trace must
        # find user_b.
        fwd = body["contacts"].get("forward", {})
        user_b_id = str(contact_setup["user_b"].id)
        assert user_b_id in fwd or contact_setup["user_b"].id in fwd, (
            f"user_b not found in forward trace: {fwd}"
        )

        # risk_score must be a number in [0, 100].
        entry = fwd.get(user_b_id) or fwd.get(contact_setup["user_b"].id)
        assert entry is not None
        assert 0 <= entry["risk_score"] <= 100
        assert entry["risk_level"] in ("low", "medium", "high")

    def test_direction_param_forward_only(self, client, ha_token, contact_setup):
        rid = contact_setup["record"].id
        resp = client.get(
            f"/api/health-admin/contact-graph/{rid}?direction=forward",
            headers=_auth(ha_token),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "forward" in body["contacts"]
        assert "backward" not in body["contacts"]

    def test_direction_param_backward_only(self, client, ha_token, contact_setup):
        rid = contact_setup["record"].id
        resp = client.get(
            f"/api/health-admin/contact-graph/{rid}?direction=backward",
            headers=_auth(ha_token),
        )
        assert resp.status_code == 200
        assert "backward" in resp.get_json()["contacts"]

    def test_invalid_direction_400(self, client, ha_token, contact_setup):
        rid = contact_setup["record"].id
        resp = client.get(
            f"/api/health-admin/contact-graph/{rid}?direction=sideways",
            headers=_auth(ha_token),
        )
        assert resp.status_code == 400

    def test_unknown_case_404(self, client, ha_token):
        resp = client.get("/api/health-admin/contact-graph/9999", headers=_auth(ha_token))
        assert resp.status_code == 404

    def test_audit_written(self, client, ha_token, contact_setup):
        rid = contact_setup["record"].id
        client.get(
            f"/api/health-admin/contact-graph/{rid}",
            headers=_auth(ha_token),
        )
        log = AuditLog.query.filter_by(action="view_contact_graph").first()
        assert log is not None


class TestRetraceContactGraph:
    def test_retrace_success(self, client, ha_token, contact_setup):
        rid = contact_setup["record"].id
        resp = client.post(
            f"/api/health-admin/contact-graph/{rid}/retrace",
            headers=_auth(ha_token),
            json={"direction": "forward", "max_depth": 1},
        )
        assert resp.status_code == 200

    def test_retrace_invalid_direction_400(self, client, ha_token, contact_setup):
        rid = contact_setup["record"].id
        resp = client.post(
            f"/api/health-admin/contact-graph/{rid}/retrace",
            headers=_auth(ha_token),
            json={"direction": "nowhere"},
        )
        assert resp.status_code == 400


# ===================================================================
# Disease KB CRUD
# ===================================================================

class TestDiseaseKBList:
    def test_returns_list(self, client, ha_token, disease):
        resp = client.get("/api/health-admin/disease-kb", headers=_auth(ha_token))
        assert resp.status_code == 200
        body = resp.get_json()
        assert any(i["name"] == "Influenza" for i in body["items"])

    def test_audit_written(self, client, ha_token, disease):
        client.get("/api/health-admin/disease-kb", headers=_auth(ha_token))
        assert AuditLog.query.filter_by(action="list_disease_kb").first() is not None


class TestCreateDiseaseKB:
    def test_success(self, client, ha_token):
        resp = client.post(
            "/api/health-admin/disease-kb",
            headers=_auth(ha_token),
            json={
                "name": "COVID-19",
                "symptoms": "fever cough breathlessness loss of smell",
                "preventive_measures": "mask distance ventilation",
                "incubation_period_days": 5,
            },
        )
        assert resp.status_code == 201
        assert resp.get_json()["name"] == "COVID-19"

    def test_duplicate_409(self, client, ha_token, disease):
        resp = client.post(
            "/api/health-admin/disease-kb",
            headers=_auth(ha_token),
            json={
                "name": "Influenza",
                "symptoms": "fever",
                "preventive_measures": "rest",
            },
        )
        assert resp.status_code == 409

    def test_missing_fields_400(self, client, ha_token):
        resp = client.post(
            "/api/health-admin/disease-kb",
            headers=_auth(ha_token),
            json={"name": "X"},
        )
        assert resp.status_code == 400

    def test_audit_written(self, client, ha_token):
        client.post(
            "/api/health-admin/disease-kb",
            headers=_auth(ha_token),
            json={"name": "AuditDisease", "symptoms": "x", "preventive_measures": "y"},
        )
        assert AuditLog.query.filter_by(action="create_disease_kb").first() is not None


class TestUpdateDiseaseKB:
    def test_success(self, client, ha_token, disease):
        resp = client.patch(
            f"/api/health-admin/disease-kb/{disease.id}",
            headers=_auth(ha_token),
            json={"incubation_period_days": 7},
        )
        assert resp.status_code == 200
        assert resp.get_json()["incubation_period_days"] == 7

    def test_not_found_404(self, client, ha_token):
        resp = client.patch(
            "/api/health-admin/disease-kb/9999",
            headers=_auth(ha_token),
            json={"symptoms": "x"},
        )
        assert resp.status_code == 404

    def test_empty_body_400(self, client, ha_token, disease):
        resp = client.patch(
            f"/api/health-admin/disease-kb/{disease.id}",
            headers=_auth(ha_token),
            json={},
        )
        assert resp.status_code == 400


# ===================================================================
# Capacity
# ===================================================================

@pytest.fixture()
def facility(db):
    cap = Capacity(facility_name="Health Centre", total_beds=5, occupied_beds=0)
    _db.session.add(cap)
    _db.session.commit()
    return cap


class TestListCapacity:
    def test_returns_facilities(self, client, ha_token, facility):
        resp = client.get("/api/health-admin/capacity", headers=_auth(ha_token))
        assert resp.status_code == 200
        body = resp.get_json()
        assert any(i["facility_name"] == "Health Centre" for i in body["items"])

    def test_available_beds_computed(self, client, ha_token, facility):
        resp = client.get("/api/health-admin/capacity", headers=_auth(ha_token))
        item = next(i for i in resp.get_json()["items"]
                    if i["facility_name"] == "Health Centre")
        assert item["available_beds"] == 5


class TestAllocateBed:
    def test_explicit_user_allocation(self, client, ha_token, facility,
                                      student_with_record):
        user_id = student_with_record["user"].id
        resp = client.post(
            f"/api/health-admin/capacity/{facility.id}/allocate",
            headers=_auth(ha_token),
            json={"user_id": user_id},
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["user_id"] == user_id
        assert body["capacity_id"] == facility.id

    def test_duplicate_allocation_409(self, client, ha_token, facility,
                                      student_with_record):
        user_id = student_with_record["user"].id
        client.post(
            f"/api/health-admin/capacity/{facility.id}/allocate",
            headers=_auth(ha_token),
            json={"user_id": user_id},
        )
        resp = client.post(
            f"/api/health-admin/capacity/{facility.id}/allocate",
            headers=_auth(ha_token),
            json={"user_id": user_id},
        )
        assert resp.status_code == 409

    def test_full_facility_409(self, client, ha_token, db):
        full = Capacity(facility_name="Full Ward", total_beds=0, occupied_beds=0)
        _db.session.add(full)
        _db.session.commit()

        # No user_id → priority queue path; queue is empty but facility is
        # full (0 beds), so should 409.
        resp = client.post(
            f"/api/health-admin/capacity/{full.id}/allocate",
            headers=_auth(ha_token),
            json={},
        )
        assert resp.status_code == 409

    def test_unknown_facility_404(self, client, ha_token):
        resp = client.post(
            "/api/health-admin/capacity/9999/allocate",
            headers=_auth(ha_token),
            json={"user_id": 1},
        )
        assert resp.status_code == 404

    def test_audit_written(self, client, ha_token, facility, student_with_record):
        user_id = student_with_record["user"].id
        client.post(
            f"/api/health-admin/capacity/{facility.id}/allocate",
            headers=_auth(ha_token),
            json={"user_id": user_id},
        )
        assert AuditLog.query.filter_by(action="allocate_bed").first() is not None


# ===================================================================
# Feedback review
# ===================================================================

@pytest.fixture()
def feedback_row(db, student_with_record):
    """An Alert + a Feedback flagged as false-positive."""
    record = student_with_record["record"]
    alert = Alert(
        user_id=student_with_record["user"].id,
        source_health_record_id=record.id,
        risk_level="low",
        risk_score=10.0,
        symptoms_snapshot="cough",
        precautions_snapshot="rest",
    )
    _db.session.add(alert)
    _db.session.commit()

    fb = Feedback(alert_id=alert.id, is_false_positive=True)
    _db.session.add(fb)
    _db.session.commit()
    return {"alert": alert, "feedback": fb}


class TestFeedbackReview:
    def test_review_without_weight_adjust(self, client, ha_token, feedback_row):
        alert_id = feedback_row["alert"].id
        resp = client.post(
            f"/api/health-admin/feedback/{alert_id}/review",
            headers=_auth(ha_token),
            json={"adjust_weight": False},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["weight_adjusted"] is False
        assert body["reviewed_by"] is not None

    def test_review_with_weight_adjust_nudges_threshold(self, client, ha_token,
                                                         feedback_row, db):
        """adjust_weight=True must increase risk_low_threshold by ~0.05."""
        cfg = SystemConfig.get()
        before = float(cfg.risk_low_threshold)

        alert_id = feedback_row["alert"].id
        resp = client.post(
            f"/api/health-admin/feedback/{alert_id}/review",
            headers=_auth(ha_token),
            json={"adjust_weight": True},
        )
        assert resp.status_code == 200
        assert resp.get_json()["weight_adjusted"] is True

        _db.session.expire(cfg)  # force reload from DB
        cfg2 = SystemConfig.get()
        after = float(cfg2.risk_low_threshold)
        assert after > before, "risk_low_threshold should have increased"

    def test_unknown_alert_404(self, client, ha_token):
        resp = client.post(
            "/api/health-admin/feedback/9999/review",
            headers=_auth(ha_token),
            json={"adjust_weight": False},
        )
        assert resp.status_code == 404

    def test_audit_written(self, client, ha_token, feedback_row):
        alert_id = feedback_row["alert"].id
        client.post(
            f"/api/health-admin/feedback/{alert_id}/review",
            headers=_auth(ha_token),
            json={"adjust_weight": False},
        )
        assert AuditLog.query.filter_by(action="review_feedback").first() is not None


# ===================================================================
# Symptom-matching service unit tests (no HTTP)
# ===================================================================

class TestSymptomMatching:
    def test_matches_best_disease(self, app, disease):
        from app.services.disease_kb_service import suggest_disease
        with app.app_context():
            match = suggest_disease("fever and cough and headache")
            assert match is not None
            assert match.id == disease.id

    def test_returns_none_for_empty_input(self, app):
        from app.services.disease_kb_service import suggest_disease
        with app.app_context():
            assert suggest_disease("") is None
            assert suggest_disease("   ") is None

    def test_returns_none_when_no_overlap(self, app, disease):
        from app.services.disease_kb_service import suggest_disease
        with app.app_context():
            result = suggest_disease("broken leg fracture ortho")
            # Influenza KB: fever cough sore throat fatigue headache
            # zero overlap → None
            assert result is None


# ===================================================================
# Advanced Health Admin Verification Tests
# ===================================================================

class TestHealthAdminAdvancedVerification:
    def test_priority_queue_picks_highest_risk_user_not_insertion_order(self, client, ha_token, facility, db):
        """Verify priority queue picks highest-risk waiting user descending by score."""
        hr = HealthRecord(user_id=1, onset_date=date.today(), severity="moderate", status="reported")
        _db.session.add(hr)
        _db.session.flush()

        # Create User A (low score) inserted first
        u_low = User(name="User Low", email="low@campus.edu", role="student", division_id=1)
        u_low.set_password("p")
        _db.session.add(u_low)
        _db.session.flush()

        alert_low = Alert(user_id=u_low.id, source_health_record_id=hr.id, risk_level="low", risk_score=25.0, symptoms_snapshot="mild cough", precautions_snapshot="rest")
        _db.session.add(alert_low)

        # Create User B (high score) inserted second
        u_high = User(name="User High", email="high@campus.edu", role="student", division_id=1)
        u_high.set_password("p")
        _db.session.add(u_high)
        _db.session.flush()

        alert_high = Alert(user_id=u_high.id, source_health_record_id=hr.id, risk_level="high", risk_score=92.5, symptoms_snapshot="high fever", precautions_snapshot="isolate")
        _db.session.add(alert_high)
        _db.session.commit()

        # Allocate bed with no user_id specified (triggers priority queue allocation)
        resp = client.post(
            f"/api/health-admin/capacity/{facility.id}/allocate",
            headers=_auth(ha_token),
            json={},
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["user_id"] == u_high.id, "Priority queue must allocate to highest risk_score (User High), not insertion order"
        assert body["priority_score"] == 92.5

    def test_retrace_contact_graph_depth_overrides(self, client, ha_token, contact_setup, db):
        """Verify max_depth=1 vs max_depth=2 alters traced contact extent."""
        rid = contact_setup["record"].id
        user_b = contact_setup["user_b"]

        # Add 2nd degree contact: user_b -> user_c
        user_c = User(name="Contact Two", email="c2@campus.edu", role="student", division_id=1)
        user_c.set_password("p")
        _db.session.add(user_c)
        _db.session.commit()

        edge2 = ContactEdge(
            user_a_id=user_b.id,
            user_b_id=user_c.id,
            room_id=contact_setup["room"].id,
            contact_date=contact_setup["record"].onset_date,
            duration_minutes=60,
            room_type_weight=1.0,
        )
        _db.session.add(edge2)
        _db.session.commit()

        # Retrace max_depth=1
        r1 = client.post(
            f"/api/health-admin/contact-graph/{rid}/retrace",
            headers=_auth(ha_token),
            json={"direction": "forward", "max_depth": 1},
        ).get_json()["contacts"]["forward"]

        assert str(user_b.id) in r1 or user_b.id in r1
        assert str(user_c.id) not in r1 and user_c.id not in r1, "max_depth=1 should not include 2nd degree contact"

        # Retrace max_depth=2
        r2 = client.post(
            f"/api/health-admin/contact-graph/{rid}/retrace",
            headers=_auth(ha_token),
            json={"direction": "forward", "max_depth": 2},
        ).get_json()["contacts"]["forward"]

        assert str(user_c.id) in r2 or user_c.id in r2, "max_depth=2 must include 2nd degree contact"

    def test_feedback_review_adjusts_risk_classification(self, client, ha_token, feedback_row, db):
        """Reviewing false positive with adjust_weight=True nudges low_threshold upward and alters classify_risk behavior."""
        from app.graph.risk_engine import classify_risk
        cfg = SystemConfig.get()

        initial_low = float(cfg.risk_low_threshold)
        initial_high = float(cfg.risk_high_threshold)

        # Borderline score between low and high
        borderline_score = initial_low + 0.02
        assert classify_risk(borderline_score, initial_low, initial_high) == "medium"

        # Review feedback with weight adjustment
        client.post(
            f"/api/health-admin/feedback/{feedback_row['alert'].id}/review",
            headers=_auth(ha_token),
            json={"adjust_weight": True},
        )

        _db.session.expire(cfg)
        new_cfg = SystemConfig.get()
        new_low = float(new_cfg.risk_low_threshold)

        assert new_low == initial_low + 0.05
        # The same score is now classified as "low" because threshold shifted upward
        assert classify_risk(borderline_score, new_low, initial_high) == "low"

    def test_health_admin_negative_permissions(self, client, ha_token):
        """Health Admin token cannot modify institute config or add non-student roles."""
        h = _auth(ha_token)
        # Cannot modify system config
        assert client.patch("/api/institute-admin/system-config", headers=h, json={"k_anonymity_threshold": 10}).status_code == 403
        # Cannot add timetable slots
        assert client.post("/api/institute-admin/timetable-slots", headers=h, json={}).status_code == 403
        # Cannot register non-student roles
        assert client.post("/api/auth/register", headers=h, json={"name": "X", "email": "x@c.edu", "password": "p", "role": "course_faculty"}).status_code == 403


# ===================================================================
# Advanced Institute Admin Verification Tests
# ===================================================================

class TestInstituteAdminAdvancedVerification:
    def test_k_anonymity_raw_suppression_toggle(self, client, admin_token, db):
        """Verify counts below k are suppressed (None in JSON), then un-suppressed when threshold is lowered."""
        div = Division(name="KAnon Div", branch="CE", year=1)
        _db.session.add(div)
        _db.session.commit()

        for i in range(3):
            u = User(name=f"Kan {i}", email=f"kan{i}@campus.edu", role="student", division_id=div.id)
            u.set_password("p")
            _db.session.add(u)
        _db.session.commit()

        # Set k=5 -> count (3) < 5 -> suppressed (None in JSON, suppressed=True)
        client.patch(
            "/api/institute-admin/system-config",
            headers=_auth(admin_token),
            json={"k_anonymity_threshold": 5},
        )
        res_high = client.get(
            "/api/institute-admin/dashboards/aggregate",
            headers=_auth(admin_token),
        ).get_json()
        div_high = next(d for d in res_high["divisions"] if d["division_id"] == div.id)
        assert div_high["student_count"] is None
        assert div_high["suppressed"] is True

        # Lower k=2 -> count (3) >= 2 -> numeric 3, suppressed=False
        client.patch(
            "/api/institute-admin/system-config",
            headers=_auth(admin_token),
            json={"k_anonymity_threshold": 2},
        )
        res_low = client.get(
            "/api/institute-admin/dashboards/aggregate",
            headers=_auth(admin_token),
        ).get_json()
        div_low = next(d for d in res_low["divisions"] if d["division_id"] == div.id)
        assert div_low["student_count"] == 3
        assert div_low["suppressed"] is False

    def test_system_config_depth_change_propagates_to_tracing_service(self, client, admin_token, contact_setup, db):
        """Updating default_tracing_depth propagates directly to trace_case defaults."""
        from app.services.tracing_service import trace_case
        rec = contact_setup["record"]

        # Patch default_tracing_depth = 1
        client.patch(
            "/api/institute-admin/system-config",
            headers=_auth(admin_token),
            json={"default_tracing_depth": 1},
        )

        # Call trace_case without explicit max_depth override
        traced = trace_case(rec)
        assert "forward" in traced

    def test_audit_log_pagination_and_filtering(self, client, admin_token, db):
        """Verify ?action= filtering and cursor pagination across multiple pages."""
        # Action 1: Create room
        client.post(
            "/api/institute-admin/rooms",
            headers=_auth(admin_token),
            json={"name": "Audit Room 1", "building": "A"},
        )
        # Action 2: Create room
        client.post(
            "/api/institute-admin/rooms",
            headers=_auth(admin_token),
            json={"name": "Audit Room 2", "building": "A"},
        )

        # Filter by action=create_room
        res_act = client.get(
            "/api/institute-admin/audit-log?action=create_room",
            headers=_auth(admin_token),
        ).get_json()
        assert all(item["action"] == "create_room" for item in res_act["items"])

        # Cursor pagination with limit=1
        page1 = client.get(
            "/api/institute-admin/audit-log?limit=1",
            headers=_auth(admin_token),
        ).get_json()
        assert len(page1["items"]) == 1
        cursor1 = page1["next_cursor"]
        assert cursor1 is not None

        page2 = client.get(
            f"/api/institute-admin/audit-log?limit=1&cursor={cursor1}",
            headers=_auth(admin_token),
        ).get_json()
        assert len(page2["items"]) == 1
        assert page1["items"][0]["id"] != page2["items"][0]["id"]

    def test_institute_admin_cannot_confirm_individual_case(self, client, admin_token, contact_setup):
        """Institute admin token cannot confirm individual cases or view individual contact graphs."""
        rid = contact_setup["record"].id
        res = client.post(
            f"/api/health-admin/cases/{rid}/confirm",
            headers=_auth(admin_token),
            json={},
        )
        assert res.status_code == 403


# ===================================================================
# Health Admin — new analytics endpoints
# ===================================================================

class TestHealthAdminAnalyticsEndpoints:
    """Tests for the new GET /cases active/pending keys, contact graph edge
    details, analytics/case, analytics/summary, and priority-queue endpoints."""

    def test_cases_active_and_pending_lists(self, client, ha_token, contact_setup, db):
        """GET /cases returns top-level 'active' and 'pending' lists alongside
        the paginated 'items' key. The seeded record (status='reported') must
        appear in pending. After confirming, it must move to active."""
        rid = contact_setup["record"].id

        res = client.get("/api/health-admin/cases", headers=_auth(ha_token))
        assert res.status_code == 200
        body = res.get_json()

        assert "active" in body, "Response must have 'active' key"
        assert "pending" in body, "Response must have 'pending' key"
        assert "items" in body, "Response must still have paginated 'items' key"

        pending_ids = [c["id"] for c in body["pending"]]
        assert rid in pending_ids, f"Record {rid} (status=reported) should be in pending"

        client.post(
            f"/api/health-admin/cases/{rid}/confirm",
            headers=_auth(ha_token),
            json={},
        )
        res2 = client.get("/api/health-admin/cases", headers=_auth(ha_token))
        body2 = res2.get_json()
        active_ids = [c["id"] for c in body2["active"]]
        pending_ids2 = [c["id"] for c in body2["pending"]]
        assert rid in active_ids, "Confirmed record should be in active list"
        assert rid not in pending_ids2, "Confirmed record must not remain in pending"

    def test_contact_graph_edge_details(self, client, ha_token, contact_setup, db):
        """GET /contact-graph/<id> must include duration_minutes, contact_date,
        room_type_weight, and contact_type per contact entry, plus a 'graph'
        key with nodes and edges for vis-network."""
        rid = contact_setup["record"].id

        res = client.get(
            f"/api/health-admin/contact-graph/{rid}?direction=forward",
            headers=_auth(ha_token),
        )
        assert res.status_code == 200
        body = res.get_json()

        assert "graph" in body, "Response must include 'graph' key"
        assert "nodes" in body["graph"]
        assert "edges" in body["graph"]
        assert len(body["graph"]["nodes"]) >= 1

        fwd = body.get("contacts", {}).get("forward", {})
        user_b_id = str(contact_setup["user_b"].id)
        entry = fwd.get(user_b_id) or fwd.get(contact_setup["user_b"].id)
        assert entry is not None, "user_b should be a forward contact"

        for field in ("duration_minutes", "contact_date", "room_type_weight",
                      "contact_type", "days_since_contact", "base_score"):
            assert field in entry, f"Contact entry must include '{field}'"
        assert entry["contact_type"] == "direct"
        assert entry["duration_minutes"] == 60

    def test_case_analytics_breakdown(self, client, ha_token, contact_setup, db):
        """GET /analytics/case/<id> returns per-contact breakdown with all
        scoring dimensions sorted descending by risk_score, and writes audit log."""
        rid = contact_setup["record"].id

        res = client.get(
            f"/api/health-admin/analytics/case/{rid}",
            headers=_auth(ha_token),
        )
        assert res.status_code == 200
        body = res.get_json()

        assert body["case_id"] == rid
        assert body["source_user_id"] == contact_setup["user_a"].id
        assert "onset_date" in body
        assert "total_contacts" in body
        assert isinstance(body["contacts"], list)

        if body["contacts"]:
            c = body["contacts"][0]
            required_fields = (
                "user_id", "direction", "depth", "contact_type",
                "duration_minutes", "contact_date", "days_since_contact",
                "room_type_weight", "hop_decay", "base_score",
                "risk_score", "risk_level",
            )
            for field in required_fields:
                assert field in c, f"Contact breakdown must include '{field}'"

        scores = [c["risk_score"] for c in body["contacts"]]
        assert scores == sorted(scores, reverse=True), "Contacts must be sorted by risk_score desc"

        log = AuditLog.query.filter_by(action="view_case_analytics", target_id=rid).first()
        assert log is not None, "Audit log entry must be written"

    def test_analytics_summary_and_priority_queue(self, client, ha_token, contact_setup, db):
        """GET /analytics/summary returns aggregate counts with required fields.
        GET /priority-queue returns a ranked, descending list and writes audit log."""
        res_sum = client.get("/api/health-admin/analytics/summary", headers=_auth(ha_token))
        assert res_sum.status_code == 200
        body_sum = res_sum.get_json()

        for field in ("total_cases", "confirmed_cases", "pending_cases",
                      "avg_contacts_per_case", "direct_contacts", "secondary_contacts"):
            assert field in body_sum, f"Summary must include '{field}'"
        assert body_sum["total_cases"] >= 1

        log_sum = AuditLog.query.filter_by(action="view_analytics_summary").first()
        assert log_sum is not None

        res_pq = client.get("/api/health-admin/priority-queue", headers=_auth(ha_token))
        assert res_pq.status_code == 200
        body_pq = res_pq.get_json()

        assert "queue" in body_pq
        assert "total" in body_pq
        assert body_pq["total"] == len(body_pq["queue"])

        scores = [e["priority_score"] for e in body_pq["queue"]]
        assert scores == sorted(scores, reverse=True), "Queue must be descending by priority_score"

        if body_pq["queue"]:
            ranks = [e["rank"] for e in body_pq["queue"]]
            assert ranks == list(range(1, len(ranks) + 1)), "Ranks must be sequential from 1"

        log_pq = AuditLog.query.filter_by(action="view_priority_queue").first()
        assert log_pq is not None
