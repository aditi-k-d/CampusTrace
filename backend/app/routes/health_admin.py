"""
Health Admin routes — Person 4.

Every route is gated by @role_required("health_admin").
Every action (read or write) creates an AuditLog row — role_hierarchy.md
explicitly notes that Health Admin's fine-grained access "is audited."
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from app.auth.rbac import role_required
from app.extensions import db
from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.capacity import Capacity, IsolationAllocation
from app.models.disease_kb import DiseaseKB
from app.models.feedback import Feedback
from app.models.health_record import HealthRecord, HEALTH_STATUSES
from app.models.system_config import SystemConfig
from app.services import disease_kb_service, capacity_service
from app.services.tracing_service import trace_case, get_case_risk_breakdown

health_admin_bp = Blueprint("health_admin", __name__)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _uid() -> int:
    return int(get_jwt_identity())


def _audit(action: str, target_type: str | None = None,
           target_id: int | None = None, details: dict | None = None) -> None:
    db.session.add(AuditLog(
        user_id=_uid(),
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
    ))


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

@health_admin_bp.get("/cases")
@role_required("health_admin")
def list_cases():
    """Returns paginated cases plus two convenience lists:
    - active:  confirmed cases (status='confirmed')
    - pending: unconfirmed/reported cases (status='reported')
    These lists are unpaginated summaries for the dashboard view.
    """
    query = HealthRecord.query

    if request.args.get("status"):
        status = request.args["status"]
        if status not in HEALTH_STATUSES:
            return jsonify(error=f"status must be one of {list(HEALTH_STATUSES)}"), 400
        query = query.filter(HealthRecord.status == status)

    if request.args.get("disease_id"):
        query = query.filter(HealthRecord.disease_id == int(request.args["disease_id"]))

    # Cursor pagination — newest first.
    limit = min(int(request.args.get("limit", 50)), 200)
    cursor = request.args.get("cursor")
    if cursor:
        try:
            query = query.filter(HealthRecord.id < int(cursor))
        except ValueError:
            return jsonify(error="Invalid cursor"), 400

    rows = query.order_by(HealthRecord.id.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    def _serialize(r):
        return {
            "id": r.id,
            "user_id": r.user_id,
            "disease_id": r.disease_id,
            "onset_date": str(r.onset_date),
            "severity": r.severity,
            "status": r.status,
            "reported_at": r.reported_at.isoformat() if r.reported_at else None,
        }

    # Build the two convenience lists (no pagination applied)
    active_records = HealthRecord.query.filter_by(status="confirmed").order_by(HealthRecord.id.desc()).all()
    pending_records = HealthRecord.query.filter_by(status="reported").order_by(HealthRecord.id.desc()).all()

    _audit("list_cases", details={
        "status": request.args.get("status"),
        "disease_id": request.args.get("disease_id"),
    })
    db.session.commit()

    return jsonify(
        items=[_serialize(r) for r in rows],
        next_cursor=str(rows[-1].id) if has_more and rows else None,
        active=[_serialize(r) for r in active_records],
        pending=[_serialize(r) for r in pending_records],
    ), 200


@health_admin_bp.post("/cases/<int:case_id>/confirm")
@role_required("health_admin")
def confirm_case(case_id: int):
    record = HealthRecord.query.get(case_id)
    if record is None:
        return jsonify(error="Health record not found"), 404

    data = request.get_json(silent=True) or {}
    disease_id = data.get("disease_id")

    if disease_id is not None:
        if not DiseaseKB.query.get(int(disease_id)):
            return jsonify(error="Disease not found in KB"), 404
        record.disease_id = int(disease_id)

    record.status = "confirmed"
    record.confirmed_by = _uid()
    _audit("confirm_case", "health_record", case_id, details={"disease_id": disease_id})
    db.session.commit()

    return jsonify(
        id=record.id, status=record.status,
        disease_id=record.disease_id, confirmed_by=record.confirmed_by,
    ), 200


# ---------------------------------------------------------------------------
# Contact graph
# ---------------------------------------------------------------------------

@health_admin_bp.get("/contact-graph/<int:case_id>")
@role_required("health_admin")
def get_contact_graph(case_id: int):
    """Returns contact trace with full edge detail (duration, date, room weight)
    plus a vis-network-compatible graph payload under the 'graph' key."""
    record = HealthRecord.query.get(case_id)
    if record is None:
        return jsonify(error="Health record not found"), 404

    direction = request.args.get("direction") or None
    max_depth_raw = request.args.get("max_depth")
    max_depth = int(max_depth_raw) if max_depth_raw else None

    if direction and direction not in ("forward", "backward", "both"):
        return jsonify(error="direction must be forward, backward, or both"), 400
    if max_depth is not None and max_depth < 1:
        return jsonify(error="max_depth must be >= 1"), 400

    results = trace_case(record, direction=direction, max_depth=max_depth)

    _audit("view_contact_graph", "health_record", case_id, details={
        "direction": direction, "max_depth": max_depth,
    })
    db.session.commit()

    return jsonify(
        case_id=case_id,
        contacts={k: v for k, v in results.items() if k != "graph"},
        graph=results.get("graph", {}),
    ), 200


@health_admin_bp.post("/contact-graph/<int:case_id>/retrace")
@role_required("health_admin")
def retrace_contact_graph(case_id: int):
    record = HealthRecord.query.get(case_id)
    if record is None:
        return jsonify(error="Health record not found"), 404

    data = request.get_json(silent=True) or {}
    direction = data.get("direction")
    max_depth = data.get("max_depth")

    if direction and direction not in ("forward", "backward", "both"):
        return jsonify(error="direction must be forward, backward, or both"), 400
    if max_depth is not None and int(max_depth) < 1:
        return jsonify(error="max_depth must be >= 1"), 400

    results = trace_case(
        record,
        direction=direction or None,
        max_depth=int(max_depth) if max_depth else None,
    )

    _audit("retrace_contact_graph", "health_record", case_id, details={
        "direction": direction, "max_depth": max_depth,
    })
    db.session.commit()

    return jsonify(
        case_id=case_id,
        contacts={k: v for k, v in results.items() if k != "graph"},
        graph=results.get("graph", {}),
    ), 200


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@health_admin_bp.get("/analytics/case/<int:case_id>")
@role_required("health_admin")
def get_case_analytics(case_id: int):
    """Per-contact risk-calculation breakdown for a given case.

    Surfaces the dimensions trace_case() already computes:
    - contact_type: direct (depth 1) vs indirect (depth 2+)
    - duration_minutes, contact_date, days_since_contact: temporal/spatial
    - room_type_weight, hop_decay: weighting factors
    - base_score, risk_score, risk_level: final classification

    No scoring is recomputed — get_case_risk_breakdown() reshapes
    trace_case()'s existing output.
    """
    record = HealthRecord.query.get(case_id)
    if record is None:
        return jsonify(error="Health record not found"), 404

    breakdown = get_case_risk_breakdown(record)

    _audit("view_case_analytics", "health_record", case_id)
    db.session.commit()

    return jsonify(
        case_id=case_id,
        source_user_id=record.user_id,
        onset_date=str(record.onset_date),
        total_contacts=len(breakdown),
        contacts=breakdown,
    ), 200


@health_admin_bp.get("/analytics/summary")
@role_required("health_admin")
def get_analytics_summary():
    """Institution-wide aggregate metrics across all traced cases.

    Returns:
    - total_cases: all health records
    - confirmed_cases: status='confirmed'
    - pending_cases: status='reported'
    - avg_contacts_per_case: average forward+backward contact count per traced case
    - secondary_contacts: total indirect (depth>=2) contacts across all cases
    - direct_contacts: total direct (depth==1) contacts across all cases
    """
    all_records = HealthRecord.query.all()
    total_cases = len(all_records)
    confirmed_cases = sum(1 for r in all_records if r.status == "confirmed")
    pending_cases = sum(1 for r in all_records if r.status == "reported")

    total_contact_count = 0
    direct_count = 0
    secondary_count = 0

    for record in all_records:
        try:
            breakdown = get_case_risk_breakdown(record)
            total_contact_count += len(breakdown)
            direct_count += sum(1 for c in breakdown if c["contact_type"] == "direct")
            secondary_count += sum(1 for c in breakdown if c["contact_type"] == "indirect")
        except Exception:
            pass  # Skip records that fail tracing (e.g. no contact data)

    avg_contacts = round(total_contact_count / total_cases, 2) if total_cases > 0 else 0.0

    _audit("view_analytics_summary")
    db.session.commit()

    return jsonify(
        total_cases=total_cases,
        confirmed_cases=confirmed_cases,
        pending_cases=pending_cases,
        avg_contacts_per_case=avg_contacts,
        direct_contacts=direct_count,
        secondary_contacts=secondary_count,
    ), 200


# ---------------------------------------------------------------------------
# Priority queue
# ---------------------------------------------------------------------------

@health_admin_bp.get("/priority-queue")
@role_required("health_admin")
def get_priority_queue():
    """Return the current waiting queue ranked by risk score (highest first).

    Each entry: {rank, user_id, priority_score}
    """
    ranked = capacity_service.get_waiting_queue_ranked()

    _audit("view_priority_queue", details={"queue_length": len(ranked)})
    db.session.commit()

    return jsonify(
        queue=ranked,
        total=len(ranked),
    ), 200


# ---------------------------------------------------------------------------
# Disease KB
# ---------------------------------------------------------------------------

@health_admin_bp.get("/disease-kb")
@role_required("health_admin")
def list_disease_kb():
    entries = DiseaseKB.query.order_by(DiseaseKB.id).all()
    _audit("list_disease_kb")
    db.session.commit()

    return jsonify(items=[
        {
            "id": e.id, "name": e.name,
            "symptoms": e.symptoms,
            "preventive_measures": e.preventive_measures,
            "incubation_period_days": e.incubation_period_days,
        }
        for e in entries
    ]), 200


@health_admin_bp.post("/disease-kb")
@role_required("health_admin")
def create_disease_kb():
    data = request.get_json(silent=True) or {}
    required = ("name", "symptoms", "preventive_measures")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify(error=f"Missing fields: {', '.join(missing)}"), 400

    if DiseaseKB.query.filter_by(name=data["name"]).first():
        return jsonify(error="Disease with this name already exists"), 409

    entry = disease_kb_service.create_disease(
        name=data["name"],
        symptoms=data["symptoms"],
        preventive_measures=data["preventive_measures"],
        incubation_period_days=data.get("incubation_period_days"),
        added_by=_uid(),
    )
    _audit("create_disease_kb", "disease_kb", entry.id)
    db.session.commit()

    return jsonify(
        id=entry.id, name=entry.name,
        symptoms=entry.symptoms,
        preventive_measures=entry.preventive_measures,
        incubation_period_days=entry.incubation_period_days,
    ), 201


@health_admin_bp.patch("/disease-kb/<int:kb_id>")
@role_required("health_admin")
def update_disease_kb(kb_id: int):
    entry = DiseaseKB.query.get(kb_id)
    if entry is None:
        return jsonify(error="Disease KB entry not found"), 404

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify(error="No fields to update"), 400

    disease_kb_service.update_disease(entry, **data)
    _audit("update_disease_kb", "disease_kb", kb_id, details=data)
    db.session.commit()

    return jsonify(
        id=entry.id, name=entry.name,
        symptoms=entry.symptoms,
        preventive_measures=entry.preventive_measures,
        incubation_period_days=entry.incubation_period_days,
    ), 200


# ---------------------------------------------------------------------------
# Capacity
# ---------------------------------------------------------------------------

@health_admin_bp.get("/capacity")
@role_required("health_admin")
def list_capacity():
    facilities = Capacity.query.all()
    _audit("list_capacity")
    db.session.commit()

    return jsonify(items=[
        {
            "id": f.id, "facility_name": f.facility_name,
            "total_beds": f.total_beds,
            "occupied_beds": f.occupied_beds,
            "available_beds": max(0, f.total_beds - f.occupied_beds),
        }
        for f in facilities
    ]), 200


@health_admin_bp.post("/capacity/<int:capacity_id>/allocate")
@role_required("health_admin")
def allocate_bed(capacity_id: int):
    """Allocate a bed.

    Two modes:
    - Body contains { "user_id": N } — allocate directly to that user.
    - Empty / no user_id  — pull the highest-priority waiting user
      from the alert risk-score queue (capacity_service).
    """
    facility = Capacity.query.get(capacity_id)
    if facility is None:
        return jsonify(error="Capacity facility not found"), 404

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if user_id is not None:
        # Manual allocation — find the user's highest risk_score.
        best_alert = (
            Alert.query
            .filter_by(user_id=int(user_id))
            .order_by(Alert.risk_score.desc())
            .first()
        )
        risk_score = float(best_alert.risk_score) if best_alert else 0.0
        allocation = capacity_service.allocate_bed(facility, int(user_id), risk_score)
    else:
        allocation = capacity_service.allocate_highest_priority(facility)

    if allocation is None:
        return jsonify(error="No bed available or user already allocated"), 409

    _audit("allocate_bed", "capacity", capacity_id, details={
        "user_id": allocation.user_id,
        "priority_score": float(allocation.priority_score),
    })
    db.session.commit()

    return jsonify(
        id=allocation.id,
        user_id=allocation.user_id,
        capacity_id=allocation.capacity_id,
        priority_score=float(allocation.priority_score),
        allocated_at=allocation.allocated_at.isoformat() if allocation.allocated_at else None,
    ), 201


# ---------------------------------------------------------------------------
# Feedback review
# ---------------------------------------------------------------------------

@health_admin_bp.post("/feedback/<int:alert_id>/review")
@role_required("health_admin")
def review_feedback(alert_id: int):
    """Mark a false-positive feedback item as reviewed.

    If adjust_weight is true, nudge the risk thresholds:
    - Increase risk_low_threshold by +0.05 (making it harder to classify
      something as even medium-risk) up to a ceiling of high_threshold-0.05.
    This is the live feedback loop that lets the classification drift based
    on observed false-positive rates, as described in methodology.md.
    """
    feedback = Feedback.query.filter_by(alert_id=alert_id).first()
    if feedback is None:
        return jsonify(error="Feedback not found for this alert"), 404

    data = request.get_json(silent=True) or {}
    adjust_weight = bool(data.get("adjust_weight", False))

    feedback.reviewed_by = _uid()
    feedback.weight_adjusted = adjust_weight

    details: dict = {"alert_id": alert_id, "adjust_weight": adjust_weight}

    if adjust_weight:
        cfg = SystemConfig.get()
        new_low = min(
            float(cfg.risk_low_threshold) + 0.05,
            float(cfg.risk_high_threshold) - 0.05,
        )
        cfg.risk_low_threshold = round(new_low, 3)
        cfg.updated_by = _uid()
        details["new_risk_low_threshold"] = float(cfg.risk_low_threshold)

    _audit("review_feedback", "feedback", feedback.id, details=details)
    db.session.commit()

    return jsonify(
        id=feedback.id,
        alert_id=feedback.alert_id,
        reviewed_by=feedback.reviewed_by,
        weight_adjusted=feedback.weight_adjusted,
    ), 200
