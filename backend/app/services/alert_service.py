"""
Alert service: tracing_service's results -> Alert rows.

A contact can appear in both the forward and backward trace (e.g. two
people who share several courses). Rather than sending two alerts,
this keeps the higher-scoring one per user — the more relevant risk
signal is the one that matters for their decision to isolate/test.
"""

from app.extensions import db
from app.models import Alert, HealthRecord, DiseaseKB

DEFAULT_SYMPTOMS = "Not specified — self-reported symptoms"
DEFAULT_PRECAUTIONS = "Monitor for symptoms and consult a health professional if you feel unwell."


def _symptoms_and_precautions(health_record: HealthRecord) -> tuple[str, str]:
    if health_record.disease_id:
        disease = DiseaseKB.query.get(health_record.disease_id)
        if disease:
            return disease.symptoms, disease.preventive_measures
    return health_record.custom_symptoms or DEFAULT_SYMPTOMS, DEFAULT_PRECAUTIONS


def generate_alerts(health_record: HealthRecord, traced_contacts: dict, session=None) -> list[Alert]:
    """traced_contacts: the dict returned by tracing_service.trace_case(),
    e.g. {'forward': {user_id: {...}}, 'backward': {...}}."""
    session = session or db.session
    symptoms, precautions = _symptoms_and_precautions(health_record)

    best_per_user: dict[int, dict] = {}
    for direction in ("forward", "backward"):
        direction_results = traced_contacts.get(direction)
        if not isinstance(direction_results, dict):
            continue
        for user_id, info in direction_results.items():
            if not isinstance(info, dict):
                continue
            if user_id not in best_per_user or info["risk_score"] > best_per_user[user_id]["risk_score"]:
                best_per_user[user_id] = info

    created = []
    for user_id, info in best_per_user.items():
        alert = Alert(
            user_id=user_id,
            source_health_record_id=health_record.id,
            risk_level=info["risk_level"],
            risk_score=info["risk_score"],
            symptoms_snapshot=symptoms,
            precautions_snapshot=precautions,
        )
        session.add(alert)
        created.append(alert)

    session.commit()
    return created