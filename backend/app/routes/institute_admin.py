"""
Institute Admin routes — Person 4.

Every route is gated by @role_required("institute_admin").
Every write operation creates an AuditLog row recording who did what.
"""

from datetime import time as dt_time

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func

from app.auth.rbac import role_required
from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.course import Batch, Course, FacultyCourseAssignment
from app.models.division import Division, Room
from app.models.enrollment import Enrollment
from app.models.health_record import HealthRecord
from app.models.system_config import SystemConfig, TRACING_DIRECTIONS
from app.models.timetable import TimetableSlot
from app.models.user import User

institute_admin_bp = Blueprint("institute_admin", __name__)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _uid() -> int:
    """Return the current user's id from the JWT (always an int)."""
    return int(get_jwt_identity())


def _audit(action: str, target_type: str | None = None,
           target_id: int | None = None, details: dict | None = None) -> None:
    """Write one AuditLog row for the calling user."""
    db.session.add(AuditLog(
        user_id=_uid(),
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
    ))
    # Flushed together with the main operation's commit.


# ---------------------------------------------------------------------------
# POST /divisions
# ---------------------------------------------------------------------------

@institute_admin_bp.post("/divisions")
@role_required("institute_admin")
def create_division():
    data = request.get_json(silent=True) or {}
    missing = [f for f in ("name", "branch", "year") if not data.get(f) and data.get(f) != 0]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400

    if Division.query.filter_by(name=data["name"]).first():
        return jsonify(error="Division name already exists"), 409

    div = Division(name=data["name"], branch=data["branch"], year=int(data["year"]))
    db.session.add(div)
    db.session.flush()  # populate div.id before audit
    _audit("create_division", "division", div.id)
    db.session.commit()

    return jsonify(id=div.id, name=div.name, branch=div.branch, year=div.year), 201


# ---------------------------------------------------------------------------
# POST /rooms
# ---------------------------------------------------------------------------

@institute_admin_bp.post("/rooms")
@role_required("institute_admin")
def create_room():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify(error="Missing fields: name"), 400

    existing = Room.query.filter_by(
        name=data["name"], building=data.get("building")
    ).first()
    if existing:
        return jsonify(error="Room already exists in this building"), 409

    room = Room(
        name=data["name"],
        building=data.get("building"),
        capacity=data.get("capacity"),
    )
    db.session.add(room)
    db.session.flush()
    _audit("create_room", "room", room.id)
    db.session.commit()

    return jsonify(
        id=room.id, name=room.name,
        building=room.building, capacity=room.capacity,
    ), 201


# ---------------------------------------------------------------------------
# POST /courses
# ---------------------------------------------------------------------------

@institute_admin_bp.post("/courses")
@role_required("institute_admin")
def create_course():
    data = request.get_json(silent=True) or {}
    required = ("division_id", "code", "name", "course_type")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400

    if data["course_type"] not in ("theory", "lab", "tutorial"):
        return jsonify(error="course_type must be theory, lab, or tutorial"), 400

    if not Division.query.get(int(data["division_id"])):
        return jsonify(error="Division not found"), 404

    course = Course(
        division_id=int(data["division_id"]),
        code=data["code"],
        name=data["name"],
        course_type=data["course_type"],
    )
    db.session.add(course)
    db.session.flush()
    _audit("create_course", "course", course.id)
    db.session.commit()

    return jsonify(
        id=course.id, division_id=course.division_id,
        code=course.code, name=course.name, course_type=course.course_type,
    ), 201


# ---------------------------------------------------------------------------
# POST /batches
# ---------------------------------------------------------------------------

@institute_admin_bp.post("/batches")
@role_required("institute_admin")
def create_batch():
    data = request.get_json(silent=True) or {}
    required = ("course_id", "name")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400

    if not Course.query.get(int(data["course_id"])):
        return jsonify(error="Course not found"), 404

    if Batch.query.filter_by(course_id=int(data["course_id"]), name=data["name"]).first():
        return jsonify(error="Batch already exists for this course"), 409

    batch = Batch(course_id=int(data["course_id"]), name=data["name"])
    db.session.add(batch)
    db.session.flush()
    _audit("create_batch", "batch", batch.id)
    db.session.commit()

    return jsonify(id=batch.id, course_id=batch.course_id, name=batch.name), 201


# ---------------------------------------------------------------------------
# POST /faculty-assignments
# ---------------------------------------------------------------------------

@institute_admin_bp.post("/faculty-assignments")
@role_required("institute_admin")
def create_faculty_assignment():
    data = request.get_json(silent=True) or {}
    required = ("faculty_id", "course_id")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400

    faculty = User.query.get(int(data["faculty_id"]))
    if not faculty or faculty.role not in ("course_faculty", "class_teacher"):
        return jsonify(error="Faculty user not found or not a faculty role"), 404

    if not Course.query.get(int(data["course_id"])):
        return jsonify(error="Course not found"), 404

    if FacultyCourseAssignment.query.filter_by(
        faculty_id=int(data["faculty_id"]),
        course_id=int(data["course_id"]),
    ).first():
        return jsonify(error="Assignment already exists"), 409

    assignment = FacultyCourseAssignment(
        faculty_id=int(data["faculty_id"]),
        course_id=int(data["course_id"]),
    )
    db.session.add(assignment)
    db.session.flush()
    _audit("create_faculty_assignment", "faculty_course_assignment", assignment.id,
           details={"faculty_id": assignment.faculty_id, "course_id": assignment.course_id})
    db.session.commit()

    return jsonify(
        id=assignment.id,
        faculty_id=assignment.faculty_id,
        course_id=assignment.course_id,
    ), 201


# ---------------------------------------------------------------------------
# POST /timetable-slots
# ---------------------------------------------------------------------------

@institute_admin_bp.post("/timetable-slots")
@role_required("institute_admin")
def create_timetable_slot():
    data = request.get_json(silent=True) or {}
    required = ("course_id", "room_id", "day_of_week", "start_time", "end_time")
    missing = [f for f in required if data.get(f) is None]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400

    if not Course.query.get(int(data["course_id"])):
        return jsonify(error="Course not found"), 404
    if not Room.query.get(int(data["room_id"])):
        return jsonify(error="Room not found"), 404

    day = int(data["day_of_week"])
    if day < 0 or day > 6:
        return jsonify(error="day_of_week must be 0 (Mon) to 6 (Sun)"), 400

    try:
        parts_s = [int(p) for p in str(data["start_time"]).split(":")]
        parts_e = [int(p) for p in str(data["end_time"]).split(":")]
        start = dt_time(*parts_s)
        end = dt_time(*parts_e)
    except (ValueError, TypeError):
        return jsonify(error="start_time / end_time must be HH:MM"), 400

    if start >= end:
        return jsonify(error="start_time must be before end_time"), 400

    batch_id = data.get("batch_id")
    if batch_id is not None:
        batch_id = int(batch_id)
        if not Batch.query.get(batch_id):
            return jsonify(error="Batch not found"), 404

    # Requirement 2: Timetable slot conflict validation (same room, same day, overlapping time)
    conflict = TimetableSlot.query.filter(
        TimetableSlot.room_id == int(data["room_id"]),
        TimetableSlot.day_of_week == day,
        TimetableSlot.start_time < end,
        TimetableSlot.end_time > start,
    ).first()

    if conflict:
        return jsonify(error="Timetable slot conflict: Room is already booked for this day and time range"), 409

    slot = TimetableSlot(
        course_id=int(data["course_id"]),
        room_id=int(data["room_id"]),
        batch_id=batch_id,
        day_of_week=day,
        start_time=start,
        end_time=end,
    )
    db.session.add(slot)
    db.session.flush()
    _audit("create_timetable_slot", "timetable_slot", slot.id)
    db.session.commit()

    return jsonify(
        id=slot.id, course_id=slot.course_id, room_id=slot.room_id,
        batch_id=slot.batch_id, day_of_week=slot.day_of_week,
        start_time=str(slot.start_time), end_time=str(slot.end_time),
    ), 201


# ---------------------------------------------------------------------------
# GET /system-config
# ---------------------------------------------------------------------------

@institute_admin_bp.get("/system-config")
@role_required("institute_admin")
def get_system_config():
    cfg = SystemConfig.get()
    return jsonify(
        k_anonymity_threshold=cfg.k_anonymity_threshold,
        default_tracing_depth=cfg.default_tracing_depth,
        default_tracing_direction=cfg.default_tracing_direction,
    ), 200


# ---------------------------------------------------------------------------
# PATCH /system-config
# ---------------------------------------------------------------------------

@institute_admin_bp.patch("/system-config")
@role_required("institute_admin")
def update_system_config():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify(error="No fields to update"), 400

    cfg = SystemConfig.get()
    changed = {}

    if "k_anonymity_threshold" in data:
        val = int(data["k_anonymity_threshold"])
        if val < 1:
            return jsonify(error="k_anonymity_threshold must be >= 1"), 400
        cfg.k_anonymity_threshold = val
        changed["k_anonymity_threshold"] = val

    if "default_tracing_depth" in data:
        val = int(data["default_tracing_depth"])
        if val < 1:
            return jsonify(error="default_tracing_depth must be >= 1"), 400
        cfg.default_tracing_depth = val
        changed["default_tracing_depth"] = val

    if "default_tracing_direction" in data:
        val = data["default_tracing_direction"]
        if val not in TRACING_DIRECTIONS:
            return jsonify(error=f"default_tracing_direction must be one of {list(TRACING_DIRECTIONS)}"), 400
        cfg.default_tracing_direction = val
        changed["default_tracing_direction"] = val

    if not changed:
        return jsonify(error="No recognized fields to update"), 400

    cfg.updated_by = _uid()
    _audit("update_system_config", "system_config", 1, details=changed)
    db.session.commit()

    return jsonify(
        k_anonymity_threshold=cfg.k_anonymity_threshold,
        default_tracing_depth=cfg.default_tracing_depth,
        default_tracing_direction=cfg.default_tracing_direction,
    ), 200


# ---------------------------------------------------------------------------
# GET /audit-log  — cursor pagination, optional filters
# ---------------------------------------------------------------------------

@institute_admin_bp.get("/audit-log")
@role_required("institute_admin")
def get_audit_log():
    limit = min(int(request.args.get("limit", 50)), 200)
    cursor = request.args.get("cursor")  # ISO-format created_at + "," + id

    query = AuditLog.query

    if request.args.get("user_id"):
        query = query.filter(AuditLog.user_id == int(request.args["user_id"]))
    if request.args.get("action"):
        query = query.filter(AuditLog.action == request.args["action"])

    if cursor:
        try:
            parts = cursor.split(",")
            cursor_id = int(parts[-1])
            query = query.filter(AuditLog.id < cursor_id)
        except (ValueError, IndexError):
            return jsonify(error="Invalid cursor"), 400

    rows = (
        query
        .order_by(AuditLog.id.desc())
        .limit(limit + 1)
        .all()
    )

    has_more = len(rows) > limit
    rows = rows[:limit]

    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = str(last.id)

    items = [
        {
            "id": r.id,
            "user_id": r.user_id,
            "action": r.action,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

    return jsonify(items=items, next_cursor=next_cursor), 200


# ---------------------------------------------------------------------------
# GET /dashboards/aggregate  — k-anonymity suppression
# ---------------------------------------------------------------------------

@institute_admin_bp.get("/dashboards/aggregate")
@role_required("institute_admin")
def dashboards_aggregate():
    cfg = SystemConfig.get()
    k = cfg.k_anonymity_threshold

    # --- per-division student counts ---
    div_rows = (
        db.session.query(
            Division.id,
            Division.name,
            Division.branch,
            func.count(User.id).label("student_count"),
        )
        .outerjoin(User, (User.division_id == Division.id) & (User.role == "student"))
        .group_by(Division.id)
        .all()
    )

    divisions = []
    for div_id, name, branch, count in div_rows:
        divisions.append({
            "division_id": div_id,
            "name": name,
            "branch": branch,
            "student_count": count if count >= k else None,
            "suppressed": count < k,
        })

    # --- per-course enrollment counts ---
    course_rows = (
        db.session.query(
            Course.id,
            Course.code,
            Course.name,
            Course.division_id,
            func.count(Enrollment.id).label("enrollment_count"),
        )
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .group_by(Course.id)
        .all()
    )

    courses = []
    for cid, code, cname, div_id, count in course_rows:
        courses.append({
            "course_id": cid,
            "code": code,
            "name": cname,
            "division_id": div_id,
            "enrollment_count": count if count >= k else None,
            "suppressed": count < k,
        })

    # --- active health cases per division ---
    case_rows = (
        db.session.query(
            Division.id.label("division_id"),
            func.count(HealthRecord.id).label("active_cases"),
        )
        .select_from(HealthRecord)
        .join(User, User.id == HealthRecord.user_id)
        .join(Division, Division.id == User.division_id)
        .filter(HealthRecord.status.in_(("reported", "confirmed")))
        .group_by(Division.id)
        .all()
    )
    case_map = {row.division_id: row.active_cases for row in case_rows}

    for d in divisions:
        count = case_map.get(d["division_id"], 0)
        d["active_cases"] = count if count >= k else None
        d["active_cases_suppressed"] = count < k

    return jsonify(
        k_anonymity_threshold=k,
        divisions=divisions,
        courses=courses,
    ), 200


# ---------------------------------------------------------------------------
# User Management: GET /users, PATCH /users/<user_id>
# ---------------------------------------------------------------------------

@institute_admin_bp.get("/users")
@role_required("institute_admin")
def list_users():
    role = request.args.get("role")
    query = User.query
    if role:
        query = query.filter_by(role=role)
    users = query.order_by(User.id).all()
    _audit("list_users")
    db.session.commit()

    return jsonify(items=[
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "division_id": u.division_id,
            "is_active": u.is_active,
        }
        for u in users
    ]), 200


@institute_admin_bp.patch("/users/<int:user_id>")
@role_required("institute_admin")
def update_user_status(user_id: int):
    if user_id == _uid():
        return jsonify(error="Cannot deactivate your own account"), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify(error="User not found"), 404

    data = request.get_json(silent=True) or {}
    if "is_active" not in data or not isinstance(data["is_active"], bool):
        return jsonify(error="is_active boolean field is required"), 400

    user.is_active = data["is_active"]
    _audit("update_user_status", "user", user_id, details={"is_active": user.is_active})
    db.session.commit()

    return jsonify(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    ), 200


# ---------------------------------------------------------------------------
# GET /dashboards/trends — Outbreak trend report per day
# ---------------------------------------------------------------------------

@institute_admin_bp.get("/dashboards/trends")
@role_required("institute_admin")
def dashboards_trends():
    cfg = SystemConfig.get()
    k = cfg.k_anonymity_threshold

    rows = (
        db.session.query(
            HealthRecord.onset_date,
            func.count(HealthRecord.id).label("case_count"),
        )
        .group_by(HealthRecord.onset_date)
        .order_by(HealthRecord.onset_date.asc())
        .all()
    )

    trends = []
    for onset_date, count in rows:
        date_str = onset_date.isoformat() if hasattr(onset_date, "isoformat") else str(onset_date)
        trends.append({
            "date": date_str,
            "case_count": count if count >= k else None,
            "suppressed": count < k,
        })

    _audit("list_outbreak_trends")
    db.session.commit()

    return jsonify(k_anonymity_threshold=k, trends=trends), 200


# ---------------------------------------------------------------------------
# GET /dashboards/by-department — Department (branch) stats
# ---------------------------------------------------------------------------

@institute_admin_bp.get("/dashboards/by-department")
@role_required("institute_admin")
def dashboards_by_department():
    cfg = SystemConfig.get()
    k = cfg.k_anonymity_threshold

    branches = [r[0] for r in db.session.query(Division.branch).distinct().all() if r[0]]

    # Cases per branch
    case_rows = (
        db.session.query(
            Division.branch,
            func.count(HealthRecord.id).label("c_count"),
        )
        .join(User, User.division_id == Division.id)
        .join(HealthRecord, HealthRecord.user_id == User.id)
        .group_by(Division.branch)
        .all()
    )
    case_map = {b: count for b, count in case_rows}

    # Alerts per branch
    from app.models.alert import Alert
    alert_rows = (
        db.session.query(
            Division.branch,
            func.count(Alert.id).label("a_count"),
        )
        .join(User, User.division_id == Division.id)
        .join(Alert, Alert.user_id == User.id)
        .group_by(Division.branch)
        .all()
    )
    alert_map = {b: count for b, count in alert_rows}

    departments = []
    for b in branches:
        c_cnt = case_map.get(b, 0)
        a_cnt = alert_map.get(b, 0)
        departments.append({
            "branch": b,
            "case_count": c_cnt if c_cnt >= k else None,
            "case_suppressed": c_cnt < k,
            "alert_count": a_cnt if a_cnt >= k else None,
            "alert_suppressed": a_cnt < k,
        })

    _audit("list_department_stats")
    db.session.commit()

    return jsonify(k_anonymity_threshold=k, departments=departments), 200


# ---------------------------------------------------------------------------
# GET /dashboards/high-overlap-locations — Rooms ranked by distinct users/courses
# ---------------------------------------------------------------------------

@institute_admin_bp.get("/dashboards/high-overlap-locations")
@role_required("institute_admin")
def dashboards_high_overlap_locations():
    cfg = SystemConfig.get()
    k = cfg.k_anonymity_threshold

    from app.models.contact_edge import ContactEdge

    user_a_sub = db.session.query(ContactEdge.room_id.label("room_id"), ContactEdge.user_a_id.label("user_id"))
    user_b_sub = db.session.query(ContactEdge.room_id.label("room_id"), ContactEdge.user_b_id.label("user_id"))
    user_union = user_a_sub.union(user_b_sub).subquery()

    u_counts = (
        db.session.query(
            user_union.c.room_id,
            func.count(user_union.c.user_id).label("u_cnt"),
        )
        .group_by(user_union.c.room_id)
        .all()
    )
    u_map = {r: cnt for r, cnt in u_counts}

    c_counts = (
        db.session.query(
            TimetableSlot.room_id,
            func.count(func.distinct(TimetableSlot.course_id)).label("c_cnt"),
        )
        .group_by(TimetableSlot.room_id)
        .all()
    )
    c_map = {r: cnt for r, cnt in c_counts}

    rooms = Room.query.all()
    locations = []
    for rm in rooms:
        u_cnt = u_map.get(rm.id, 0)
        c_cnt = c_map.get(rm.id, 0)
        locations.append({
            "room_id": rm.id,
            "room_name": rm.name,
            "building": rm.building,
            "distinct_users": u_cnt if u_cnt >= k else None,
            "distinct_courses": c_cnt if c_cnt >= k else None,
            "suppressed": u_cnt < k,
        })

    _audit("list_high_overlap_locations")
    db.session.commit()

    return jsonify(k_anonymity_threshold=k, locations=locations), 200


# ---------------------------------------------------------------------------
# GET /dashboards/analytics — Exposure by location & department
# ---------------------------------------------------------------------------

@institute_admin_bp.get("/dashboards/analytics")
@role_required("institute_admin")
def dashboards_analytics():
    cfg = SystemConfig.get()
    k = cfg.k_anonymity_threshold

    from app.models.contact_edge import ContactEdge

    loc_rows = (
        db.session.query(
            Room.name.label("room_name"),
            func.count(ContactEdge.id).label("edge_count"),
        )
        .join(ContactEdge, ContactEdge.room_id == Room.id)
        .group_by(Room.id)
        .all()
    )

    exposure_by_location = [
        {
            "room_name": r_name,
            "exposure_count": count if count >= k else None,
            "suppressed": count < k,
        }
        for r_name, count in loc_rows
    ]

    dept_rows = (
        db.session.query(
            Division.branch,
            func.count(ContactEdge.id).label("edge_count"),
        )
        .join(User, User.division_id == Division.id)
        .join(
            ContactEdge,
            (ContactEdge.user_a_id == User.id) | (ContactEdge.user_b_id == User.id),
        )
        .group_by(Division.branch)
        .all()
    )

    exposure_by_department = [
        {
            "branch": branch,
            "exposure_count": count if count >= k else None,
            "suppressed": count < k,
        }
        for branch, count in dept_rows
    ]

    _audit("list_analytics")
    db.session.commit()

    return jsonify(
        k_anonymity_threshold=k,
        exposure_by_location=exposure_by_location,
        exposure_by_department=exposure_by_department,
    ), 200


# ---------------------------------------------------------------------------
# GET /dashboards/event-exposures — Event-wise exposure counts
# ---------------------------------------------------------------------------

@institute_admin_bp.get("/dashboards/event-exposures")
@role_required("institute_admin")
def dashboards_event_exposures():
    cfg = SystemConfig.get()
    k = cfg.k_anonymity_threshold

    from app.models.presence import Presence

    rows = (
        db.session.query(
            Course.code.label("course_code"),
            Course.name.label("course_name"),
            Room.name.label("room_name"),
            Presence.presence_date,
            func.count(Presence.user_id).label("attendee_count"),
        )
        .join(TimetableSlot, Presence.slot_id == TimetableSlot.id)
        .join(Course, TimetableSlot.course_id == Course.id)
        .join(Room, Presence.room_id == Room.id)
        .group_by(Course.id, Room.id, Presence.presence_date)
        .all()
    )

    events = []
    for ccode, cname, rname, pdate, count in rows:
        date_str = pdate.isoformat() if hasattr(pdate, "isoformat") else str(pdate)
        events.append({
            "course": f"{ccode} ({cname})",
            "room": rname,
            "date": date_str,
            "exposure_count": count if count >= k else None,
            "suppressed": count < k,
        })

    _audit("list_event_exposures")
    db.session.commit()

    return jsonify(k_anonymity_threshold=k, events=events), 200

