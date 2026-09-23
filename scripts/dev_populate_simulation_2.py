"""Generate a second, proximity-based CampusTrace development simulation.

Prerequisite: run ``dev_populate.py`` once to create the campus, timetable,
enrollments, and disease KB. This script adds an isolated 14-day simulation
window before the first simulation's default 21-day window and does not reset
the database. It replaces presence/contact rows only inside its own date
window so reruns are idempotent.

Presence session type and duration are derived from the timetable slot/course
type and its start/end times; the current schema stores those source fields
rather than duplicating them on Presence.
"""

import argparse
import os
import random
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from itertools import combinations

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "backend"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app
from app.extensions import db
from app.models import (
    Course, DiseaseKB, Enrollment, FacultyCourseAssignment, HealthRecord,
    Presence, ContactEdge, TimetableSlot, User,
)


DEFAULT_SEED = 20260923
WINDOW_DAYS = 14
ROOM_WEIGHT = {"lab": 1.2, "tutorial": 1.1, "theory": 1.0}


def duration_minutes(start: time, end: time) -> int:
    anchor = date.today()
    return max(1, int((datetime.combine(anchor, end) - datetime.combine(anchor, start)).total_seconds() // 60))


def attendees_for_slot(slot: TimetableSlot) -> list[int]:
    query = Enrollment.query.filter_by(course_id=slot.course_id)
    if slot.batch_id is None:
        query = query.filter(Enrollment.batch_id.is_(None))
    else:
        query = query.filter(Enrollment.batch_id == slot.batch_id)
    ids = {row.student_id for row in query.all()}
    ids.update(row.faculty_id for row in FacultyCourseAssignment.query.filter_by(course_id=slot.course_id).all())
    return sorted(ids)


def proximity_pairs(roster: list[int], present_ids: list[int], rng: random.Random):
    """Stable seating by roster order, probabilistic local contacts by distance."""
    if len(present_ids) < 2:
        return []
    # A compact grid gives each attendee a few nearby neighbors even in labs.
    width = max(4, int(len(roster) ** 0.5) + 1)
    seats = {uid: (i % width, i // width) for i, uid in enumerate(roster)}
    pairs = []
    for a, b in combinations(present_ids, 2):
        ax, ay = seats[a]
        bx, by = seats[b]
        distance = abs(ax - bx) + abs(ay - by)
        if distance == 1:
            chance = 0.98
        elif distance == 2:
            chance = 0.90
        elif distance == 3:
            chance = 0.72
        elif distance == 4:
            chance = 0.50
        elif distance == 5:
            chance = 0.30
        elif distance == 6:
            chance = 0.15
        else:
            continue
        if rng.random() < chance:
            pairs.append((min(a, b), max(a, b), distance))
    return pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=WINDOW_DAYS, help="Simulation window length (default: 14 days)")
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for reproducible simulation (default: {DEFAULT_SEED})",
    )
    parser.add_argument("--end-date", type=date.fromisoformat,
                        default=date.today() - timedelta(days=21),
                        help="Inclusive simulation end date (default: 21 days before today)")
    args = parser.parse_args()
    if not 7 <= args.days <= 21:
        parser.error("--days must be between 7 and 21")

    app = create_app("development")
    rng = random.Random(args.seed)
    with app.app_context():
        students = User.query.filter_by(role="student", is_active=True).order_by(User.id).all()
        slots = TimetableSlot.query.order_by(TimetableSlot.course_id, TimetableSlot.id).all()
        if not 175 <= len(students) <= 275:
            raise SystemExit(f"Expected 175–275 active students; found {len(students)}. Run dev_populate.py first.")
        if not slots:
            raise SystemExit("No timetable sessions found. Run dev_populate.py first.")

        end_date = args.end_date
        start_date = end_date - timedelta(days=args.days - 1)
        dates = [start_date + timedelta(days=i) for i in range(args.days)]
        # Replace only this simulation's records, leaving the rest of the DB intact.
        Presence.query.filter(Presence.presence_date.between(start_date, end_date)).delete(synchronize_session=False)
        ContactEdge.query.filter(ContactEdge.contact_date.between(start_date, end_date)).delete(synchronize_session=False)
        HealthRecord.query.filter_by(custom_symptoms="Synthetic simulation case").delete(synchronize_session=False)
        db.session.flush()

        attendees = {slot.id: attendees_for_slot(slot) for slot in slots}
        slots_by_weekday = defaultdict(list)
        courses = {course.id: course for course in Course.query.all()}
        for slot in slots:
            slots_by_weekday[slot.day_of_week].append(slot)

        # Seat maps persist for each course across repeated meetings. A shared
        # elective therefore creates a modest number of recurring bridge users.
        presence_rows = []
        edge_rows = []
        seen_edge_keys = set()
        for day in dates:
            for slot in slots_by_weekday[day.weekday()]:
                roster = attendees[slot.id]
                if len(roster) < 2:
                    continue
                course = courses.get(slot.course_id)
                session_type = getattr(course, "course_type", "theory")
                # Attendance variation across meetings while preserving repeated classmates.
                # Keep attendance high enough for the default 14-day window
                # to meet the intended 2,000–4,000 presence target while still
                # allowing a small amount of realistic variation between meetings.
                attendance_rate = 0.99 if session_type == "lab" else 0.995
                present = [uid for uid in roster if rng.random() < attendance_rate]
                if len(present) < 2:
                    continue
                minutes = duration_minutes(slot.start_time, slot.end_time)
                for uid in present:
                    presence_rows.append(Presence(
                        user_id=uid, room_id=slot.room_id, slot_id=slot.id,
                        presence_date=day, start_time=slot.start_time, end_time=slot.end_time,
                    ))
                for user_a, user_b, distance in proximity_pairs(roster, present, rng):
                    # contact_edges is keyed by pair/date/room (not session),
                    # so represent a repeated same-day room encounter once.
                    edge_key = (user_a, user_b, day, slot.room_id)
                    if edge_key in seen_edge_keys:
                        continue
                    seen_edge_keys.add(edge_key)
                    # Nearer seats tend to share more of the session; distant
                    # sampled contacts get shorter durations. Keep each event
                    # within the Presence interval and above zero.
                    fraction = {1: (0.25, 0.75), 2: (0.15, 0.50), 3: (0.08, 0.30), 4: (0.05, 0.15), 5: (0.04, 0.12), 6: (0.03, 0.08)}[distance]
                    contact_minutes = max(1, min(minutes, round(minutes * rng.uniform(*fraction))))
                    edge_rows.append(ContactEdge(
                        user_a_id=user_a, user_b_id=user_b, room_id=slot.room_id,
                        contact_date=day, duration_minutes=contact_minutes,
                        room_type_weight=ROOM_WEIGHT.get(session_type, 1.0),
                    ))

        # Enforce requested volume bands with a clear diagnostic rather than
        # silently writing a simulation that misses the intended scale.
        presence_count, event_count = len(presence_rows), len(edge_rows)
        if not 2_000 <= presence_count <= 4_000:
            db.session.rollback()
            raise SystemExit(f"Generated {presence_count:,} presences (target 2,000–4,000). Try --days 7–21 or inspect timetable density.")
        if not 15_000 <= event_count <= 35_000:
            db.session.rollback()
            raise SystemExit(f"Generated {event_count:,} contact events (target 15,000–35,000). Adjust room attendance/seating density and rerun.")

        db.session.add_all(presence_rows)
        db.session.add_all(edge_rows)

        case_count = rng.randint(5, 10)
        case_students = rng.sample(students, case_count)
        disease = DiseaseKB.query.filter_by(name="Seasonal Flu").first()
        if disease is None:
            disease = DiseaseKB(
                name="Simulation Flu", symptoms="fever cough fatigue",
                preventive_measures="rest fluids and avoid close contact",
                incubation_period_days=2,
            )
            db.session.add(disease)
            db.session.flush()
        for student in case_students:
            onset = end_date - timedelta(days=rng.randint(3, min(10, args.days - 1)))
            db.session.add(HealthRecord(
                user_id=student.id, disease_id=disease.id,
                custom_symptoms="Synthetic simulation case",
                onset_date=onset, severity="moderate", status="confirmed",
            ))

        db.session.commit()
        print("Second proximity simulation created")
        print(f"Students: {len(students)} | Initial health cases: {case_count}")
        print(f"Window: {start_date.isoformat()} through {end_date.isoformat()} ({args.days} days)")
        print(f"Presence records: {presence_count:,} | Raw contact events: {event_count:,}")
        print("Session type/duration are available from course type and timetable start/end times.")


if __name__ == "__main__":
    main()
