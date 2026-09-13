"""
Contact graph builder: Presence -> ContactEdge rows.

Building edges pairwise is inherently O(k^2) for k people sharing a
room+slot+date — but k is bounded by room/class capacity, so this is
only a problem if you naively build edges across the WHOLE
institution's presence table at once. This groups by (room_id,
slot_id, date) first and only pairs people within a group, so the
real cost scales with room occupancy, not institution size.

room_type_weight isn't stored on Room — it's derived from the course
type of the slot (lab > tutorial > theory), since risk from shared
lab equipment/proximity is meaningfully different from a lecture hall.
"""

from datetime import datetime, date as date_cls
from itertools import combinations

from app.extensions import db
from app.models import Presence, ContactEdge, TimetableSlot, Course

ROOM_TYPE_WEIGHT = {
    "lab": 1.20,
    "tutorial": 1.10,
    "theory": 1.00,
}
DEFAULT_ROOM_TYPE_WEIGHT = 1.00


def _duration_minutes(start_time, end_time) -> int:
    anchor = date_cls.today()
    return int((datetime.combine(anchor, end_time) - datetime.combine(anchor, start_time)).total_seconds() // 60)


def _room_type_weight_for_slot(slot: TimetableSlot) -> float:
    course = Course.query.get(slot.course_id)
    if course is None:
        return DEFAULT_ROOM_TYPE_WEIGHT
    return ROOM_TYPE_WEIGHT.get(course.course_type, DEFAULT_ROOM_TYPE_WEIGHT)


def build_edges_for_date(target_date: date_cls, session=None) -> int:
    """Idempotent per (pair, date, room) via ContactEdge's unique
    constraint check below. Returns number of edges created."""
    session = session or db.session

    presences = Presence.query.filter_by(presence_date=target_date).all()

    groups: dict[tuple[int, int], list[Presence]] = {}
    for p in presences:
        groups.setdefault((p.room_id, p.slot_id), []).append(p)

    created = 0
    for (room_id, slot_id), group in groups.items():
        if len(group) < 2:
            continue  # no contact possible with fewer than 2 people

        slot = TimetableSlot.query.get(slot_id)
        if slot is None:
            continue
        weight = _room_type_weight_for_slot(slot)
        duration = _duration_minutes(group[0].start_time, group[0].end_time)

        for p_a, p_b in combinations(group, 2):
            user_a_id, user_b_id = sorted((p_a.user_id, p_b.user_id))

            exists = ContactEdge.query.filter_by(
                user_a_id=user_a_id, user_b_id=user_b_id, contact_date=target_date, room_id=room_id
            ).first()
            if exists:
                continue

            session.add(
                ContactEdge(
                    user_a_id=user_a_id,
                    user_b_id=user_b_id,
                    room_id=room_id,
                    contact_date=target_date,
                    duration_minutes=duration,
                    room_type_weight=weight,
                )
            )
            created += 1

    session.commit()
    return created