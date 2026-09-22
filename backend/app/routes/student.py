"""
Student routes — Person 2.

Every route is gated by @role_required("student") and scopes all operations
strictly to the calling student's JWT identity.
"""

from datetime import datetime, date
import re

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.auth.rbac import role_required
from app.extensions import db
from app.models.user import User
from app.models.course import Course, Batch
from app.models.enrollment import Enrollment
from app.models.health_record import HealthRecord, SEVERITY_LEVELS
from app.models.alert import Alert
from app.models.absence_flag import AbsenceFlag
from app.models.feedback import Feedback
from app.models.disease_kb import DiseaseKB
from app.services import tracing_service, alert_service

student_bp = Blueprint("student", __name__)


def _uid() -> int:
    """Return the calling student's user ID from the JWT."""
    return int(get_jwt_identity())


# ---------------------------------------------------------------------------
# POST /student/register-batches
# ---------------------------------------------------------------------------
@student_bp.post("/register-batches")
@role_required("student")
def register_batches():
    data = request.get_json(silent=True) or {}
    selections = data.get("batch_selections")

    if not isinstance(selections, list) or not selections:
        return jsonify(error="batch_selections list is required"), 400

    student_id = _uid()
    created_or_updated = []

    for sel in selections:
        if not isinstance(sel, dict):
            return jsonify(error="Each item in batch_selections must be an object"), 400
        course_id = sel.get("course_id")
        batch_id = sel.get("batch_id")

        if not course_id or not batch_id:
            return jsonify(error="course_id and batch_id are required for each selection"), 400

        course = Course.query.get(int(course_id))
        if not course:
            return jsonify(error=f"Course {course_id} not found"), 404

        batch = Batch.query.get(int(batch_id))
        if not batch:
            return jsonify(error=f"Batch {batch_id} not found"), 404

        if batch.course_id != course.id:
            return jsonify(error=f"Batch {batch_id} does not belong to course {course_id}"), 400

        enrollment = Enrollment.query.filter_by(student_id=student_id, course_id=course.id).first()
        if enrollment:
            enrollment.batch_id = batch.id
        else:
            enrollment = Enrollment(student_id=student_id, course_id=course.id, batch_id=batch.id)
            db.session.add(enrollment)

        created_or_updated.append(enrollment)

    db.session.commit()

    return jsonify([
        {"id": e.id, "course_id": e.course_id, "batch_id": e.batch_id}
        for e in created_or_updated
    ]), 201


# ---------------------------------------------------------------------------
# GET /student/courses
# ---------------------------------------------------------------------------
@student_bp.get("/courses")
@role_required("student")
def get_courses():
    student_id = _uid()
    student = User.query.get(student_id)
    if not student:
        return jsonify(error="User not found"), 404

    enrollments = Enrollment.query.filter_by(student_id=student_id).all()
    enrollment_map = {e.course_id: e for e in enrollments}

    course_ids = set(enrollment_map.keys())
    if student.division_id:
        div_courses = Course.query.filter_by(division_id=student.division_id).all()
        for c in div_courses:
            course_ids.add(c.id)

    courses = Course.query.filter(Course.id.in_(course_ids)).all() if course_ids else []

    res = []
    for c in courses:
        en = enrollment_map.get(c.id)
        batch_id = en.batch_id if en else None
        batch_name = en.batch.name if (en and en.batch) else None
        batches = [{"id": b.id, "name": b.name} for b in Batch.query.filter_by(course_id=c.id).all()]
        res.append({
            "course_id": c.id,
            "code": c.code,
            "name": c.name,
            "course_type": c.course_type,
            "batch_id": batch_id,
            "batch_name": batch_name,
            "batches": batches,
        })

    return jsonify(res), 200


# ---------------------------------------------------------------------------
# POST /student/health-report
# ---------------------------------------------------------------------------
@student_bp.post("/health-report")
@role_required("student")
def report_health():
    data = request.get_json(silent=True) or {}
    onset_str = data.get("onset_date")
    severity = data.get("severity")

    if not onset_str or not severity:
        return jsonify(error="Missing required fields: onset_date, severity"), 400

    if severity not in SEVERITY_LEVELS:
        return jsonify(error=f"severity must be one of {list(SEVERITY_LEVELS)}"), 400

    try:
        onset_date = datetime.strptime(str(onset_str), "%Y-%m-%d").date()
    except ValueError:
        return jsonify(error="onset_date must be in YYYY-MM-DD format"), 400

    disease_id = data.get("disease_id")
    custom_symptoms = data.get("custom_symptoms")

    if disease_id is not None:
        disease_id = int(disease_id)
        if not DiseaseKB.query.get(disease_id):
            return jsonify(error="Disease not found"), 404
    elif not custom_symptoms:
        return jsonify(error="Either disease_id or custom_symptoms must be provided"), 400

    student_id = _uid()
    hr = HealthRecord(
        user_id=student_id,
        disease_id=disease_id,
        custom_symptoms=custom_symptoms,
        onset_date=onset_date,
        severity=severity,
        status="reported",
    )
    db.session.add(hr)
    db.session.commit()

    # Synchronous tracing and alert generation (Phase 1 scale)
    traced = tracing_service.trace_case(hr)
    alerts = alert_service.generate_alerts(hr, traced)

    return jsonify(
        id=hr.id,
        user_id=hr.user_id,
        disease_id=hr.disease_id,
        custom_symptoms=hr.custom_symptoms,
        onset_date=hr.onset_date.isoformat(),
        severity=hr.severity,
        status=hr.status,
        alerts_generated=len(alerts),
    ), 201


# ---------------------------------------------------------------------------
# GET /student/health-records
# ---------------------------------------------------------------------------
@student_bp.get("/health-records")
@role_required("student")
def get_health_records():
    student_id = _uid()
    records = HealthRecord.query.filter_by(user_id=student_id).order_by(HealthRecord.id.desc()).all()

    res = [
        {
            "id": r.id,
            "disease_id": r.disease_id,
            "disease_name": r.disease.name if r.disease else None,
            "custom_symptoms": r.custom_symptoms,
            "onset_date": r.onset_date.isoformat() if r.onset_date else None,
            "severity": r.severity,
            "status": r.status,
            "created_at": r.reported_at.isoformat() if r.reported_at else None,
            "reported_at": r.reported_at.isoformat() if r.reported_at else None,
        }
        for r in records
    ]
    return jsonify(res), 200


# ---------------------------------------------------------------------------
# GET /student/diseases
# ---------------------------------------------------------------------------
@student_bp.get("/diseases")
@role_required("student")
def get_diseases():
    diseases = DiseaseKB.query.all()
    res = [
        {
            "id": d.id,
            "name": d.name,
            "icd_code": d.icd_code,
            "symptoms": d.symptoms,
            "preventive_measures": d.preventive_measures,
        }
        for d in diseases
    ]
    return jsonify(res), 200


# ---------------------------------------------------------------------------
# GET /student/alerts
# ---------------------------------------------------------------------------
@student_bp.get("/alerts")
@role_required("student")
def get_alerts():
    student_id = _uid()
    alerts = Alert.query.filter_by(user_id=student_id).order_by(Alert.created_at.desc()).all()

    res = [
        {
            "id": a.id,
            "risk_level": a.risk_level,
            "risk_score": float(a.risk_score),
            "symptoms": a.symptoms_snapshot,
            "precautions": a.precautions_snapshot,
            "preventive_measures": a.precautions_snapshot,
            "recommended_action": a.precautions_snapshot,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
        }
        for a in alerts
    ]
    return jsonify(res), 200


# ---------------------------------------------------------------------------
# POST /student/alerts/<id>/acknowledge
# ---------------------------------------------------------------------------
@student_bp.post("/alerts/<int:alert_id>/acknowledge")
@role_required("student")
def acknowledge_alert(alert_id: int):
    student_id = _uid()
    alert = Alert.query.filter_by(id=alert_id, user_id=student_id).first()
    if not alert:
        return jsonify(error="Alert not found"), 404

    alert.acknowledged_at = datetime.utcnow()
    db.session.commit()

    return jsonify(
        id=alert.id,
        acknowledged_at=alert.acknowledged_at.isoformat(),
    ), 200


# ---------------------------------------------------------------------------
# POST /student/alerts/<id>/false-positive
# ---------------------------------------------------------------------------
@student_bp.post("/alerts/<int:alert_id>/false-positive")
@role_required("student")
def report_false_positive(alert_id: int):
    student_id = _uid()
    alert = Alert.query.filter_by(id=alert_id, user_id=student_id).first()
    if not alert:
        return jsonify(error="Alert not found"), 404

    existing = Feedback.query.filter_by(alert_id=alert.id).first()
    if existing:
        return jsonify(error="Feedback already submitted for this alert"), 409

    fb = Feedback(alert_id=alert.id, is_false_positive=True)
    db.session.add(fb)
    db.session.commit()

    return jsonify(
        id=fb.id,
        alert_id=fb.alert_id,
        is_false_positive=fb.is_false_positive,
    ), 201


# ---------------------------------------------------------------------------
# GET /student/absence-flags
# ---------------------------------------------------------------------------
@student_bp.get("/absence-flags")
@role_required("student")
def get_absence_flags():
    student_id = _uid()
    flags = AbsenceFlag.query.filter_by(student_id=student_id).order_by(AbsenceFlag.flagged_date.desc()).all()

    res = [
        {
            "id": f.id,
            "course_id": f.course_id,
            "course_name": f.course.name if f.course else None,
            "flagged_date": f.flagged_date.isoformat() if isinstance(f.flagged_date, (date, datetime)) else str(f.flagged_date),
            "reason_category": f.reason_category,
            "state": f.state,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in flags
    ]
    return jsonify(res), 200


# ---------------------------------------------------------------------------
# POST /student/absence-flags/<id>/respond
# ---------------------------------------------------------------------------
@student_bp.post("/absence-flags/<int:flag_id>/respond")
@role_required("student")
def respond_absence_flag(flag_id: int):
    student_id = _uid()
    flag = AbsenceFlag.query.filter_by(id=flag_id, student_id=student_id).first()
    if not flag:
        return jsonify(error="Absence flag not found"), 404

    data = request.get_json(silent=True) or {}
    if "confirm" not in data or not isinstance(data["confirm"], bool):
        return jsonify(error="confirm boolean field is required"), 400

    flag.state = "confirmed" if data["confirm"] else "dismissed"
    db.session.commit()

    return jsonify(id=flag.id, state=flag.state), 200


# ---------------------------------------------------------------------------
# POST /student/self-assessment
# ---------------------------------------------------------------------------
@student_bp.post("/self-assessment")
@role_required("student")
def self_assessment():
    data = request.get_json(silent=True) or {}
    raw_symptoms = data.get("symptoms") or data.get("custom_symptoms")

    if not raw_symptoms:
        return jsonify(error="symptoms field (list or string) is required"), 400

    if isinstance(raw_symptoms, list):
        text = " ".join(str(s) for s in raw_symptoms)
    else:
        text = str(raw_symptoms)

    stop_words = {"a", "an", "the", "and", "or", "in", "of", "with", "for", "to", "i", "have", "has", "feeling", "am", "my", "is"}
    tokens = set(re.findall(r"\w+", text.lower())) - stop_words

    if not tokens:
        return jsonify(
            matched_disease=None,
            guidance="No specific symptoms parsed.",
            recommended_action="If you feel unwell, consult the campus health center.",
        ), 200

    all_diseases = DiseaseKB.query.all()
    best_match = None
    best_score = 0

    for d in all_diseases:
        d_tokens = set(re.findall(r"\w+", d.symptoms.lower())) - stop_words
        overlap = len(tokens & d_tokens)
        if overlap > best_score:
            best_score = overlap
            best_match = d

    if best_match and best_score > 0:
        return jsonify(
            matched_disease=best_match.name,
            guidance=f"Your symptoms align with known characteristics of {best_match.name}.",
            recommended_action=best_match.preventive_measures or "Consult campus health service and monitor your health.",
        ), 200

    return jsonify(
        matched_disease=None,
        guidance="No matching disease pattern was found in the Knowledge Base for your symptoms.",
        recommended_action="Monitor your health and visit the campus health center if symptoms persist or worsen.",
    ), 200
