"""
Presence builder: TimetableSlot + Enrollment -> Presence rows.

Run nightly (or on-demand) for a target date. Deliberately processes
one timetable slot at a time rather than a single giant query across
the whole institution — each slot's attendee count is bounded by
course/batch size, so this stays cheap per slot even as the number of
divisions grows. See the scalability discussion on graph_builder.py's
docstring for why this matters more than it looks.
"""

from datetime import date as date_cls

from app.extensions import db
from app.models import TimetableSlot, Enrollment, FacultyCourseAssignment, Presence


def _attendee_ids_for_slot(slot: TimetableSlot) -> set[int]:
    """Everyone expected in this slot: enrolled students (matching the
    slot's batch, or unbatched for theory) plus faculty assigned to the
    course."""
    student_query = Enrollment.query.filter_by(course_id=slot.course_id)
    if slot.batch_id is not None:
        student_query = student_query.filter(Enrollment.batch_id == slot.batch_id)
    else:
        student_query = student_query.filter(Enrollment.batch_id.is_(None))
    student_ids = {e.student_id for e in student_query.all()}

    faculty_ids = {
        fca.faculty_id
        for fca in FacultyCourseAssignment.query.filter_by(course_id=slot.course_id).all()
    }

    return student_ids | faculty_ids


def build_presence_for_date(target_date: date_cls, session=None) -> int:
    """Idempotent: safe to re-run for the same date (existing rows are
    skipped via the presence table's unique constraint check below).
    Returns the number of Presence rows created."""
    session = session or db.session
    day_of_week = target_date.weekday()  # Monday=0 .. Sunday=6

    slots = TimetableSlot.query.filter_by(day_of_week=day_of_week).all()

    created = 0
    for slot in slots:
        attendee_ids = _attendee_ids_for_slot(slot)
        if not attendee_ids:
            continue

        existing = {
            p.user_id
            for p in Presence.query.filter_by(slot_id=slot.id, presence_date=target_date).all()
        }

        for user_id in attendee_ids - existing:
            session.add(
                Presence(
                    user_id=user_id,
                    room_id=slot.room_id,
                    slot_id=slot.id,
                    presence_date=target_date,
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                )
            )
            created += 1

    session.commit()
    return created