"""
/auth/register, /auth/login, /auth/me

Registration policy (this is a deliberate design decision, not an
oversight — see the docstring on register()):
  - 'student' can self-register freely (per role_hierarchy.md, students
    register themselves and pick their division at first login).
  - Every other role (course_faculty, class_teacher, health_admin,
    institute_admin) requires the CALLER to already be an authenticated
    institute_admin — per role_hierarchy.md, "Manage user roles/
    permissions (add/remove faculty, health admins)" is an Institute
    Admin capability, not open self-service.
  - Bootstrap exception: if zero institute_admin accounts exist yet,
    the very first institute_admin registration is allowed
    unauthenticated. After that one succeeds, the gate closes.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from app.extensions import db
from app.auth.rbac import current_user_role
from app.models.user import User, ROLES, ROLE_STUDENT, ROLE_INSTITUTE_ADMIN

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}

    required = ("name", "email", "password", "role")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400

    role = data["role"]
    if role not in ROLES:
        return jsonify(error=f"Invalid role. Must be one of {list(ROLES)}"), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify(error="Email already registered"), 409

    if role != ROLE_STUDENT:
        admin_exists = User.query.filter_by(role=ROLE_INSTITUTE_ADMIN).first() is not None
        if admin_exists:
            # Gate closed — caller must already be an institute_admin.
            if current_user_role() != ROLE_INSTITUTE_ADMIN:
                return (
                    jsonify(error="Only an institute_admin can create this role"),
                    403,
                )
        elif role != ROLE_INSTITUTE_ADMIN:
            # No admin exists yet, and this isn't the bootstrap admin
            # registration either — nobody is around to authorize it.
            return (
                jsonify(error="No institute_admin exists yet to authorize this role"),
                403,
            )
        # else: role == institute_admin and none exists yet -> bootstrap allowed

    division_id = data.get("division_id")
    if role in (ROLE_STUDENT,) and division_id is None:
        # Division is required at registration for students per
        # role_hierarchy.md ("Register: select division...").
        return jsonify(error="division_id is required for student registration"), 400

    user = User(name=data["name"], email=data["email"], role=role, division_id=division_id)
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    return jsonify(id=user.id, name=user.name, email=user.email, role=user.role), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify(error="email and password are required"), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.is_active or not user.check_password(password):
        return jsonify(error="Invalid email or password"), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "division_id": user.division_id},
    )
    return jsonify(
        access_token=access_token,
        user={"id": user.id, "name": user.name, "email": user.email, "role": user.role},
    ), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if user is None:
        return jsonify(error="User not found"), 404
    return jsonify(
        id=user.id, name=user.name, email=user.email, role=user.role, division_id=user.division_id
    ), 200