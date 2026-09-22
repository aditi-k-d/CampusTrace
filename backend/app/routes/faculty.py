"""
Course Faculty routes — Person 3.

Requires @role_required("course_faculty", "class_teacher").
Scoped strictly to courses assigned to the calling user via FacultyCourseAssignment.
"""

from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.auth.rbac import role_required
from app.extensions import db
from app.models.course import Course, FacultyCourseAssignment
from app.models.enrollment import Enrollment
from app.models.presence import Presence
from app.models.health_record import HealthRecord
from app.models.absence_flag import AbsenceFlag, ABSENCE_STATES
from app.models.user import User, ROLE_STUDENT

faculty_bp = Blueprint("faculty", __name__)


def _uid() -> int:
    """Return current user's ID from the JWT."""
    return int(get_jwt_identity())


def _is_assigned(faculty_id: int, course_id: int) -> bool:
    """Check if the given faculty member is assigned to the course."""
    return FacultyCourseAssignment.query.filter_by(
        faculty_id=faculty_id, course_id=course_id
    ).first() is not None


# ---------------------------------------------------------------------------
# GET /faculty/courses/<course_id>/attendance
# ---------------------------------------------------------------------------
@faculty_bp.get("/courses/<int:course_id>/attendance")
@role_required("course_faculty", "class_teacher")
def get_course_attendance(course_id: int):
    faculty_id = _uid()
    if not _is_assigned(faculty_id, course_id):
        return jsonify(error="Forbidden: You are not assigned to this course"), 403

    date_str = request.args.get("date")
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify(error="date query parameter must be YYYY-MM-DD"), 400
    else:
        target_date = date.today()

    records = (
        Presence.query.join(Presence.slot)
        .filter(Presence.presence_date == target_date)
        .filter(Presence.slot.has(course_id=course_id))
        .all()
    )

    present_users = [
        {
            "user_id": p.user_id,
            "user_name": p.user.name if p.user else None,
            "slot_id": p.slot_id,
            "room_name": p.room.name if p.room else None,
            "presence_date": p.presence_date.isoformat(),
            "start_time": str(p.start_time),
            "end_time": str(p.end_time),
        }
        for p in records
    ]

    return jsonify(
        course_id=course_id,
        date=target_date.isoformat(),
        total_present=len(present_users),
        present_users=present_users,
    ), 200


# ---------------------------------------------------------------------------
# GET /faculty/courses/<course_id>/health-summary
# Aggregate health status counts only (never individual diagnoses per role_hierarchy.md)
# ---------------------------------------------------------------------------
@faculty_bp.get("/courses/<int:course_id>/health-summary")
@role_required("course_faculty", "class_teacher")
def get_course_health_summary(course_id: int):
    faculty_id = _uid()
    if not _is_assigned(faculty_id, course_id):
        return jsonify(error="Forbidden: You are not assigned to this course"), 403

    course = Course.query.get(course_id)
    if not course:
        return jsonify(error="Course not found"), 404

    # Enrolled students in this course
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    student_ids = {e.student_id for e in enrollments}

    # Also include students in course's division if division exists
    if course.division_id:
        div_students = User.query.filter_by(division_id=course.division_id, role=ROLE_STUDENT).all()
        for s in div_students:
            student_ids.add(s.id)

    total_students = len(student_ids)
    if not student_ids:
        return jsonify(
            course_id=course_id,
            total_students=0,
            under_observation=0,
            confirmed_cases=0,
        ), 200

    # Active health records for these students
    records = HealthRecord.query.filter(
        HealthRecord.user_id.in_(student_ids),
        HealthRecord.status.in_(("reported", "confirmed"))
    ).all()

    under_observation_user_ids = {r.user_id for r in records}
    confirmed_user_ids = {r.user_id for r in records if r.status == "confirmed"}

    return jsonify(
        course_id=course_id,
        total_students=total_students,
        under_observation=len(under_observation_user_ids),
        confirmed_cases=len(confirmed_user_ids),
    ), 200


# ---------------------------------------------------------------------------
# POST /faculty/absence-flags
# ---------------------------------------------------------------------------
@faculty_bp.post("/absence-flags")
@role_required("course_faculty", "class_teacher")
def create_absence_flag():
    data = request.get_json(silent=True) or {}
    required = ("student_id", "course_id", "flagged_date", "reason_category")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify(error=f"Missing required fields: {', '.join(missing)}"), 400

    faculty_id = _uid()
    course_id = int(data["course_id"])
    if not _is_assigned(faculty_id, course_id):
        return jsonify(error="Forbidden: You are not assigned to this course"), 403

    student_id = int(data["student_id"])
    student = User.query.get(student_id)
    if not student or student.role != ROLE_STUDENT:
        return jsonify(error="Student not found"), 404

    try:
        flagged_date = datetime.strptime(str(data["flagged_date"]), "%Y-%m-%d").date()
    except ValueError:
        return jsonify(error="flagged_date must be YYYY-MM-DD format"), 400

    flag = AbsenceFlag(
        student_id=student_id,
        course_id=course_id,
        faculty_id=faculty_id,
        flagged_date=flagged_date,
        reason_category=str(data["reason_category"]),
        state="pending",
    )
    db.session.add(flag)
    db.session.commit()

    return jsonify(
        id=flag.id,
        student_id=flag.student_id,
        course_id=flag.course_id,
        flagged_date=flag.flagged_date.isoformat(),
        reason_category=flag.reason_category,
        state=flag.state,
    ), 201


# ---------------------------------------------------------------------------
# GET /faculty/absence-flags
# ---------------------------------------------------------------------------
@faculty_bp.get("/absence-flags")
@role_required("course_faculty", "class_teacher")
def get_absence_flags():
    faculty_id = _uid()
    flags = AbsenceFlag.query.filter_by(faculty_id=faculty_id).order_by(AbsenceFlag.created_at.desc()).all()

    res = [
        {
            "id": f.id,
            "student_id": f.student_id,
            "student_name": f.student.name if f.student else None,
            "course_id": f.course_id,
            "course_code": f.course.code if f.course else None,
            "flagged_date": f.flagged_date.isoformat(),
            "reason_category": f.reason_category,
            "state": f.state,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in flags
    ]
    return jsonify(res), 200
