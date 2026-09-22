"""
Class Teacher routes — Person 3.

Requires @role_required("class_teacher").
Scoped to the class teacher's assigned division.
"""

from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.auth.rbac import role_required
from app.extensions import db
from app.models.user import User, ROLE_STUDENT
from app.models.division import Division
from app.models.course import Course, FacultyCourseAssignment
from app.models.enrollment import Enrollment
from app.models.presence import Presence
from app.models.health_record import HealthRecord
from app.models.absence_flag import AbsenceFlag

class_teacher_bp = Blueprint("class_teacher", __name__)

ESCALATION_ROLLING_WINDOW_DAYS = 14


def _uid() -> int:
    """Return current user's ID from the JWT."""
    return int(get_jwt_identity())


def _get_teacher_divisions(user_id: int) -> set[int]:
    """Find all division IDs associated with this class teacher
    (either directly via User.division_id or via assigned courses)."""
    user = User.query.get(user_id)
    div_ids = set()
    if user and user.division_id:
        div_ids.add(user.division_id)

    assignments = FacultyCourseAssignment.query.filter_by(faculty_id=user_id).all()
    for a in assignments:
        if a.course and a.course.division_id:
            div_ids.add(a.course.division_id)

    return div_ids


# ---------------------------------------------------------------------------
# GET /class-teacher/division-pattern
# ---------------------------------------------------------------------------
@class_teacher_bp.get("/division-pattern")
@role_required("class_teacher")
def get_division_pattern():
    teacher_id = _uid()
    teacher_div_ids = _get_teacher_divisions(teacher_id)

    target_div_id = request.args.get("division_id")
    if target_div_id:
        target_div_id = int(target_div_id)
        if teacher_div_ids and target_div_id not in teacher_div_ids:
            return jsonify(error="Forbidden: Not assigned to this division"), 403
        div_id = target_div_id
    else:
        if not teacher_div_ids:
            return jsonify(error="No division assigned to teacher"), 400
        div_id = next(iter(teacher_div_ids))

    division = Division.query.get(div_id)
    if not division:
        return jsonify(error="Division not found"), 404

    students = User.query.filter_by(division_id=div_id, role=ROLE_STUDENT).all()
    student_ids = [s.id for s in students]

    # Active health cases in division
    active_cases_count = 0
    if student_ids:
        active_cases_count = (
            HealthRecord.query.filter(
                HealthRecord.user_id.in_(student_ids),
                HealthRecord.status.in_(("reported", "confirmed")),
            ).count()
        )

    # Division courses + elective courses taken by division's students
    enrolled_course_ids = []
    if student_ids:
        enrolled_course_ids = [
            row[0]
            for row in db.session.query(Enrollment.course_id)
            .filter(Enrollment.student_id.in_(student_ids))
            .distinct()
            .all()
        ]

    div_course_ids = [c.id for c in Course.query.filter_by(division_id=div_id).all()]
    all_course_ids = list(set(enrolled_course_ids + div_course_ids))

    courses = Course.query.filter(Course.id.in_(all_course_ids)).all() if all_course_ids else []
    course_stats = []

    for c in courses:
        flag_query = AbsenceFlag.query.filter_by(course_id=c.id)
        presence_query = Presence.query.join(Presence.slot).filter(Presence.slot.has(course_id=c.id))

        if student_ids:
            flag_query = flag_query.filter(AbsenceFlag.student_id.in_(student_ids))
            presence_query = presence_query.filter(Presence.user_id.in_(student_ids))

        flag_count = flag_query.count()
        presence_count = presence_query.count()

        course_stats.append({
            "course_id": c.id,
            "code": c.code,
            "name": c.name,
            "course_type": c.course_type,
            "absence_flags_count": flag_count,
            "presence_count": presence_count,
        })

    return jsonify(
        division_id=div_id,
        division_name=division.name,
        branch=division.branch,
        year=division.year,
        total_students=len(students),
        active_health_cases=active_cases_count,
        courses=course_stats,
    ), 200


# ---------------------------------------------------------------------------
# GET /class-teacher/escalations
# Rolling window: 14 days (students flagged across >1 distinct course)
# ---------------------------------------------------------------------------
@class_teacher_bp.get("/escalations")
@role_required("class_teacher")
def get_escalations():
    teacher_id = _uid()
    teacher_div_ids = _get_teacher_divisions(teacher_id)

    cutoff_date = date.today() - timedelta(days=ESCALATION_ROLLING_WINDOW_DAYS)

    query = AbsenceFlag.query.filter(AbsenceFlag.flagged_date >= cutoff_date)

    if teacher_div_ids:
        div_students = User.query.filter(User.division_id.in_(teacher_div_ids), User.role == ROLE_STUDENT).all()
        student_ids = [s.id for s in div_students]
        if student_ids:
            query = query.filter(AbsenceFlag.student_id.in_(student_ids))
        else:
            return jsonify(rolling_window_days=ESCALATION_ROLLING_WINDOW_DAYS, escalations=[]), 200

    flags = query.all()

    # Group flags by student_id
    student_flags = {}
    for f in flags:
        student_flags.setdefault(f.student_id, []).append(f)

    escalations = []
    for sid, s_flags in student_flags.items():
        distinct_course_ids = set(f.course_id for f in s_flags)
        if len(distinct_course_ids) > 1:
            student = User.query.get(sid)
            escalations.append({
                "student_id": sid,
                "student_name": student.name if student else None,
                "student_email": student.email if student else None,
                "flag_count": len(s_flags),
                "distinct_courses_count": len(distinct_course_ids),
                "course_ids": list(distinct_course_ids),
                "reason_categories": list(set(f.reason_category for f in s_flags)),
            })

    return jsonify(
        rolling_window_days=ESCALATION_ROLLING_WINDOW_DAYS,
        escalations=escalations,
    ), 200


# ---------------------------------------------------------------------------
# POST /class-teacher/enrollment-changes/approve or /enrollment-changes/<id>/approve
# ---------------------------------------------------------------------------
def _process_enrollment_approval(enrollment_id: int | None, data: dict):
    teacher_id = _uid()
    teacher_div_ids = _get_teacher_divisions(teacher_id)

    student_id = data.get("student_id")
    course_id = data.get("course_id")
    batch_id = data.get("batch_id")

    enrollment = None
    if enrollment_id and enrollment_id > 0:
        enrollment = Enrollment.query.get(enrollment_id)

    if not enrollment and student_id and course_id:
        enrollment = Enrollment.query.filter_by(student_id=int(student_id), course_id=int(course_id)).first()

    if enrollment:
        student = User.query.get(enrollment.student_id)
        if teacher_div_ids and student and student.division_id and student.division_id not in teacher_div_ids:
            return jsonify(error="Forbidden: Student does not belong to your assigned division"), 403

        if batch_id is not None:
            enrollment.batch_id = int(batch_id) if batch_id else None

        db.session.commit()
        return jsonify(
            message="Enrollment change approved",
            enrollment_id=enrollment.id,
            student_id=enrollment.student_id,
            course_id=enrollment.course_id,
            batch_id=enrollment.batch_id,
            status="approved",
        ), 200

    if not student_id or not course_id:
        return jsonify(error="Enrollment not found and missing student_id / course_id to create one"), 404

    student = User.query.get(int(student_id))
    if not student or student.role != ROLE_STUDENT:
        return jsonify(error="Student not found"), 404

    if teacher_div_ids and student.division_id and student.division_id not in teacher_div_ids:
        return jsonify(error="Forbidden: Student does not belong to your assigned division"), 403

    course = Course.query.get(int(course_id))
    if not course:
        return jsonify(error="Course not found"), 404

    # Create new Enrollment row on approval
    new_enrollment = Enrollment(
        student_id=int(student_id),
        course_id=int(course_id),
        batch_id=int(batch_id) if batch_id else None,
    )
    db.session.add(new_enrollment)
    db.session.commit()

    return jsonify(
        message="Enrollment change approved and created",
        enrollment_id=new_enrollment.id,
        student_id=new_enrollment.student_id,
        course_id=new_enrollment.course_id,
        batch_id=new_enrollment.batch_id,
        status="approved",
    ), 201


@class_teacher_bp.post("/enrollment-changes/<int:enrollment_id>/approve")
@role_required("class_teacher")
def approve_enrollment_change_by_id(enrollment_id: int):
    data = request.get_json(silent=True) or {}
    return _process_enrollment_approval(enrollment_id, data)


@class_teacher_bp.post("/enrollment-changes/approve")
@role_required("class_teacher")
def approve_enrollment_change_generic():
    data = request.get_json(silent=True) or {}
    enrollment_id = data.get("enrollment_id")
    return _process_enrollment_approval(enrollment_id, data)
