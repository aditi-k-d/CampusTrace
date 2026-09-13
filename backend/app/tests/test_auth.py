"""
Unit tests for app/auth/* — register, login, /me, and @role_required.
Run: cd backend && pytest app/tests/test_auth.py -v
"""

import pytest

from app.auth.rbac import role_required


def register(client, **overrides):
    payload = {
        "name": "Test User",
        "email": "user@campus.edu",
        "password": "testpass123",
        "role": "student",
        "division_id": 1,
    }
    payload.update(overrides)
    return client.post("/api/auth/register", json=payload)


def login(client, email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password})


# --- register ---

def test_student_can_self_register(client):
    resp = register(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["role"] == "student"
    assert body["email"] == "user@campus.edu"


def test_register_rejects_duplicate_email(client):
    register(client, email="dup@campus.edu")
    resp = register(client, email="dup@campus.edu")
    assert resp.status_code == 409


def test_register_rejects_missing_fields(client):
    resp = client.post("/api/auth/register", json={"name": "No Email"})
    assert resp.status_code == 400


def test_register_rejects_invalid_role(client):
    resp = register(client, role="dictator")
    assert resp.status_code == 400


def test_student_register_requires_division_id(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "N", "email": "n@campus.edu", "password": "p", "role": "student"},
    )
    assert resp.status_code == 400


def test_first_institute_admin_bootstraps_unauthenticated(client):
    resp = register(client, name="Admin", email="admin@campus.edu", role="institute_admin", division_id=None)
    assert resp.status_code == 201
    assert resp.get_json()["role"] == "institute_admin"


def test_second_institute_admin_blocked_without_auth(client):
    register(client, name="Admin1", email="admin1@campus.edu", role="institute_admin", division_id=None)
    resp = register(client, name="Admin2", email="admin2@campus.edu", role="institute_admin", division_id=None)
    assert resp.status_code == 403


def test_elevated_role_requires_admin_auth(client):
    register(client, name="Admin", email="admin@campus.edu", role="institute_admin", division_id=None)
    resp = register(client, name="Faculty", email="fac@campus.edu", role="course_faculty", division_id=None)
    assert resp.status_code == 403


def test_admin_can_create_elevated_role(client):
    register(client, name="Admin", email="admin@campus.edu", role="institute_admin", division_id=None)
    admin_token = login(client, "admin@campus.edu", "testpass123").get_json()["access_token"]

    resp = client.post(
        "/api/auth/register",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Faculty", "email": "fac@campus.edu", "password": "testpass123", "role": "course_faculty"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["role"] == "course_faculty"


def test_student_cannot_create_elevated_role(client):
    register(client, name="Admin", email="admin@campus.edu", role="institute_admin", division_id=None)
    register(client, name="Student", email="stu@campus.edu")
    stu_token = login(client, "stu@campus.edu", "testpass123").get_json()["access_token"]

    resp = client.post(
        "/api/auth/register",
        headers={"Authorization": f"Bearer {stu_token}"},
        json={"name": "Faculty", "email": "fac@campus.edu", "password": "testpass123", "role": "course_faculty"},
    )
    assert resp.status_code == 403


# --- login ---

def test_login_succeeds_with_correct_credentials(client):
    register(client)
    resp = login(client, "user@campus.edu", "testpass123")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "access_token" in body
    assert body["user"]["email"] == "user@campus.edu"


def test_login_fails_with_wrong_password(client):
    register(client)
    resp = login(client, "user@campus.edu", "wrongpass")
    assert resp.status_code == 401


def test_login_fails_for_unknown_email(client):
    resp = login(client, "ghost@campus.edu", "whatever")
    assert resp.status_code == 401


def test_login_requires_both_fields(client):
    resp = client.post("/api/auth/login", json={"email": "user@campus.edu"})
    assert resp.status_code == 400


# --- /me ---

def test_me_returns_current_user_with_valid_token(client):
    register(client)
    token = login(client, "user@campus.edu", "testpass123").get_json()["access_token"]

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["email"] == "user@campus.edu"


def test_me_rejects_missing_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_rejects_garbage_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code in (401, 422)  # flask-jwt-extended returns 422 for malformed tokens


# --- @role_required ---

def test_role_required_allows_matching_role(app, client):
    @app.get("/api/_test/admin-only")
    @role_required("institute_admin")
    def _stub():
        return {"ok": True}

    register(client, name="Admin", email="admin@campus.edu", role="institute_admin", division_id=None)
    token = login(client, "admin@campus.edu", "testpass123").get_json()["access_token"]

    resp = client.get("/api/_test/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_role_required_blocks_wrong_role(app, client):
    @app.get("/api/_test/admin-only-2")
    @role_required("institute_admin")
    def _stub2():
        return {"ok": True}

    register(client)  # a plain student
    token = login(client, "user@campus.edu", "testpass123").get_json()["access_token"]

    resp = client.get("/api/_test/admin-only-2", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_role_required_blocks_missing_token(app, client):
    @app.get("/api/_test/admin-only-3")
    @role_required("institute_admin")
    def _stub3():
        return {"ok": True}

    resp = client.get("/api/_test/admin-only-3")
    assert resp.status_code == 401