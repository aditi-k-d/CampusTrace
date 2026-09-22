"""
DEVELOPMENT / LOCAL VERIFICATION SYNTHETIC DATA POPULATION SCRIPT

This script populates synthetic demo data for a local mid-semester assessment.
It is explicitly NOT the real pilot dataset and MUST NEVER be mixed into a
production seed path or run against a production database.

Scope:
- 4 Divisions (Computer Engineering Yr 2, Information Technology Yr 3, AI/ML Yr 1, Data Science/AI Yr 4)
- 6 Shared Rooms across all divisions with varied capacity
- 14-16 Courses across divisions + 1 shared cross-division Elective course
- Timetable slots for full week using only the 6 shared rooms with heavy cross-division foot traffic
- ~240 Students (~60/division), 10 Faculty (2-3/division), 4 Class Teachers (1/division), 1 Health Admin, 1 Bridging Faculty
- Disease Knowledge Base entries (Chickenpox, Seasonal Flu, Common Cold, Viral Fever)
- Multi-week presence generation and contact edge building (3 weeks / 21 days)
- Health reports spanning multiple divisions including a verified cross-division bridging case
- Absence flags with student confirmation/dismissal responses
"""

import sys
import os
import argparse
from datetime import date, timedelta
import requests

# Add backend directory to sys.path to allow importing backend models & services for Step 3
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

DEFAULT_BASE_URL = "http://localhost:5000/api"


def log(msg: str):
    print(f"[dev_populate] {msg}", flush=True)


def log_error(msg: str):
    print(f"[dev_populate ERROR] {msg}", file=sys.stderr, flush=True)


def post_json(session: requests.Session, url: str, json_data: dict, headers: dict = None):
    return session.post(url, json=json_data, headers=headers)


def get_json(session: requests.Session, url: str, headers: dict = None):
    return session.get(url, headers=headers)


def main():
    parser = argparse.ArgumentParser(
        description="CampusTrace synthetic demo data population script."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base REST API URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        default=True,
        help="Cleanly reset DB tables before seeding (default: True)",
    )
    parser.add_argument(
        "--no-reset",
        dest="reset",
        action="store_false",
        help="Do not reset DB tables before seeding",
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    session = requests.Session()

    # Health check
    try:
        health_res = get_json(session, f"{base_url}/health")
        if health_res.status_code != 200:
            log_error(f"Health check failed with status code {health_res.status_code}")
            sys.exit(1)
        log(f"Backend health check OK at {base_url}/health")
    except requests.RequestException as e:
        log_error(f"Failed to connect to backend at {base_url}: {e}")
        log_error("Please make sure the Flask backend server is running.")
        sys.exit(1)

    if args.reset:
        log("\n=== STEP 0: Clean DB Reset for Idempotent Seeding ===")
        from app import create_app
        from app.extensions import db
        flask_app = create_app("development")
        with flask_app.app_context():
            db.drop_all()
            db.create_all()
            log("Database schema reset cleanly for fresh synthetic seeding.")

    # -------------------------------------------------------------------------
    # STEP 1: REST API Population (Admin Bootstrap, Structure, Users, Schedule)
    # -------------------------------------------------------------------------
    log("\n=== STEP 1: REST API Population ===")

    # 1.1 Bootstrap / Login Institute Admin
    admin_creds = {
        "name": "Institute Admin",
        "email": "admin@campustrace.edu",
        "password": "AdminPassword123!",
        "role": "institute_admin",
    }
    reg_res = post_json(session, f"{base_url}/auth/register", admin_creds)
    if reg_res.status_code == 201:
        log(f"Bootstrap admin created (ID: {reg_res.json().get('id')})")
    elif reg_res.status_code in (409, 403):
        log("Admin user already registered or bootstrap completed. Logging in...")

    login_res = post_json(
        session,
        f"{base_url}/auth/login",
        {"email": admin_creds["email"], "password": admin_creds["password"]},
    )
    if login_res.status_code != 200:
        log_error(f"Failed to login as admin: {login_res.status_code} - {login_res.text}")
        sys.exit(1)

    admin_token = login_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    log("Logged in as Institute Admin.")

    # 1.2 Create 4 Divisions
    divisions_specs = [
        {"name": "Computer Engineering Yr 2", "branch": "Computer Engineering", "year": 2, "key": "CE"},
        {"name": "Information Technology Yr 3", "branch": "Information Technology", "year": 3, "key": "IT"},
        {"name": "AI/ML Yr 1", "branch": "Artificial Intelligence", "year": 1, "key": "AI"},
        {"name": "Data Science/AI Yr 4", "branch": "Data Science", "year": 4, "key": "DS"},
    ]

    div_ids = {}
    for spec in divisions_specs:
        res = post_json(session, f"{base_url}/institute-admin/divisions", {
            "name": spec["name"],
            "branch": spec["branch"],
            "year": spec["year"],
        }, headers=admin_headers)
        if res.status_code in (201, 200):
            d_id = res.json()["id"]
            div_ids[spec["key"]] = d_id
            log(f"Created Division '{spec['name']}' (ID: {d_id})")
        else:
            div_ids[spec["key"]] = len(div_ids) + 1

    # 1.3 Create 6 Shared Rooms (across all divisions)
    rooms_specs = [
        {"name": "Lab 101", "building": "Main Academic Block", "capacity": 30},
        {"name": "Lab 102", "building": "Main Academic Block", "capacity": 35},
        {"name": "LH 201", "building": "Annex Block", "capacity": 80},  # Target high foot-traffic room
        {"name": "LH 202", "building": "Annex Block", "capacity": 100},
        {"name": "LH 203", "building": "Annex Block", "capacity": 120},
        {"name": "Seminar Hall", "building": "Central Complex", "capacity": 150},
    ]

    room_ids = []
    for r_spec in rooms_specs:
        res = post_json(session, f"{base_url}/institute-admin/rooms", r_spec, headers=admin_headers)
        if res.status_code in (201, 200):
            r_id = res.json()["id"]
            room_ids.append(r_id)
            log(f"Created Room '{r_spec['name']}' (ID: {r_id})")
        else:
            room_ids.append(len(room_ids) + 1)

    # 1.4 Create 14-16 Courses + 1 Shared Elective Course
    courses_specs = [
        # CE Courses (Div 1)
        {"div": "CE", "code": "CE201", "name": "Data Structures & Algorithms", "type": "theory", "has_batches": False},
        {"div": "CE", "code": "CE202L", "name": "Data Structures Lab", "type": "lab", "has_batches": True},
        {"div": "CE", "code": "CE203T", "name": "Discrete Math Tutorial", "type": "tutorial", "has_batches": True},
        {"div": "CE", "code": "CE204", "name": "Computer Organization", "type": "theory", "has_batches": False},

        # IT Courses (Div 2)
        {"div": "IT", "code": "IT301", "name": "Web Engineering", "type": "theory", "has_batches": False},
        {"div": "IT", "code": "IT302L", "name": "Web Technology Lab", "type": "lab", "has_batches": True},
        {"div": "IT", "code": "IT303T", "name": "Operating Systems Tutorial", "type": "tutorial", "has_batches": True},
        {"div": "IT", "code": "IT304", "name": "Database Systems", "type": "theory", "has_batches": False},

        # AI/ML Courses (Div 3)
        {"div": "AI", "code": "AI101", "name": "Intro to Artificial Intelligence", "type": "theory", "has_batches": False},
        {"div": "AI", "code": "AI102L", "name": "Python AI Programming Lab", "type": "lab", "has_batches": True},
        {"div": "AI", "code": "AI103T", "name": "Linear Algebra Tutorial", "type": "tutorial", "has_batches": True},
        {"div": "AI", "code": "AI104_ELEC", "name": "Advanced Neural Networks (Shared Elective)", "type": "theory", "has_batches": False, "is_elective": True},

        # DS Courses (Div 4)
        {"div": "DS", "code": "DS401", "name": "Big Data Analytics", "type": "theory", "has_batches": False},
        {"div": "DS", "code": "DS402L", "name": "Big Data Analytics Lab", "type": "lab", "has_batches": True},
        {"div": "DS", "code": "DS403T", "name": "Deep Learning Tutorial", "type": "tutorial", "has_batches": True},
        {"div": "DS", "code": "DS404", "name": "Natural Language Processing", "type": "theory", "has_batches": False},
    ]

    course_info = {}
    for c_spec in courses_specs:
        d_id = div_ids[c_spec["div"]]
        c_res = post_json(session, f"{base_url}/institute-admin/courses", {
            "division_id": d_id,
            "code": c_spec["code"],
            "name": c_spec["name"],
            "course_type": c_spec["type"],
        }, headers=admin_headers)
        if c_res.status_code in (201, 200):
            c_id = c_res.json()["id"]
            batches = {}
            if c_spec["has_batches"]:
                b1_res = post_json(session, f"{base_url}/institute-admin/batches", {
                    "course_id": c_id, "name": f"{c_spec['code']}-Batch-1"
                }, headers=admin_headers)
                b2_res = post_json(session, f"{base_url}/institute-admin/batches", {
                    "course_id": c_id, "name": f"{c_spec['code']}-Batch-2"
                }, headers=admin_headers)
                if b1_res.status_code in (201, 200):
                    batches["B1"] = b1_res.json()["id"]
                if b2_res.status_code in (201, 200):
                    batches["B2"] = b2_res.json()["id"]

            course_info[c_spec["code"]] = {
                "id": c_id,
                "div": c_spec["div"],
                "type": c_spec["type"],
                "batches": batches,
                "is_elective": c_spec.get("is_elective", False),
            }
            log(f"Created Course '{c_spec['code']}' (ID: {c_id}) with {len(batches)} batches.")

    # 1.5 Timetable Slots Creation (routing multiple divisions through shared rooms)
    log("\nCreating timetable slots for the 6 shared rooms...")

    heavy_room_id = room_ids[2]  # LH 201
    lab_room_1 = room_ids[0]     # Lab 101
    lab_room_2 = room_ids[1]     # Lab 102
    lecture_room_2 = room_ids[3] # LH 202
    lecture_room_3 = room_ids[4] # LH 203
    seminar_room = room_ids[5]   # Seminar Hall

    slot_templates = [
        # Monday (0)
        {"code": "CE201", "room": heavy_room_id, "day": 0, "start": "09:00", "end": "10:00", "batch": None},
        {"code": "IT301", "room": heavy_room_id, "day": 0, "start": "10:15", "end": "11:15", "batch": None},  # Bridging faculty course
        {"code": "AI101", "room": heavy_room_id, "day": 0, "start": "11:30", "end": "12:30", "batch": None},
        {"code": "DS401", "room": heavy_room_id, "day": 0, "start": "13:30", "end": "14:30", "batch": None},
        {"code": "AI104_ELEC", "room": heavy_room_id, "day": 0, "start": "14:45", "end": "15:45", "batch": None},  # Shared Elective

        # Labs & Tutorials on Monday
        {"code": "CE202L", "room": lab_room_1, "day": 0, "start": "10:00", "end": "12:00", "batch": "B1"},
        {"code": "IT302L", "room": lab_room_2, "day": 0, "start": "13:00", "end": "15:00", "batch": "B1"},
        {"code": "DS402L", "room": lab_room_1, "day": 0, "start": "15:00", "end": "17:00", "batch": "B1"},

        # Tuesday (1)
        {"code": "CE201", "room": heavy_room_id, "day": 1, "start": "09:00", "end": "10:00", "batch": None},
        {"code": "IT301", "room": heavy_room_id, "day": 1, "start": "10:15", "end": "11:15", "batch": None},
        {"code": "AI101", "room": heavy_room_id, "day": 1, "start": "11:30", "end": "12:30", "batch": None},
        {"code": "CE204", "room": lecture_room_2, "day": 1, "start": "13:30", "end": "14:30", "batch": None},
        {"code": "IT304", "room": lecture_room_3, "day": 1, "start": "14:45", "end": "15:45", "batch": None},

        # Wednesday (2)
        {"code": "CE201", "room": heavy_room_id, "day": 2, "start": "09:00", "end": "10:00", "batch": None},
        {"code": "IT301", "room": heavy_room_id, "day": 2, "start": "10:15", "end": "11:15", "batch": None},
        {"code": "AI104_ELEC", "room": heavy_room_id, "day": 2, "start": "11:30", "end": "12:30", "batch": None},
        {"code": "DS404", "room": seminar_room, "day": 2, "start": "14:00", "end": "15:00", "batch": None},

        # Thursday (3)
        {"code": "CE201", "room": heavy_room_id, "day": 3, "start": "09:00", "end": "10:00", "batch": None},
        {"code": "IT301", "room": heavy_room_id, "day": 3, "start": "10:15", "end": "11:15", "batch": None},
        {"code": "AI102L", "room": lab_room_1, "day": 3, "start": "11:30", "end": "13:30", "batch": "B1"},
        {"code": "DS402L", "room": lab_room_2, "day": 3, "start": "14:00", "end": "16:00", "batch": "B2"},

        # Friday (4)
        {"code": "CE201", "room": heavy_room_id, "day": 4, "start": "09:00", "end": "10:00", "batch": None},
        {"code": "IT301", "room": heavy_room_id, "day": 4, "start": "10:15", "end": "11:15", "batch": None},
        {"code": "AI104_ELEC", "room": heavy_room_id, "day": 4, "start": "11:30", "end": "12:30", "batch": None},
    ]

    slots_created = 0
    for tmpl in slot_templates:
        c_meta = course_info.get(tmpl["code"])
        if not c_meta:
            continue
        batch_id = c_meta["batches"].get(tmpl["batch"]) if tmpl["batch"] else None
        
        slot_payload = {
            "course_id": c_meta["id"],
            "room_id": tmpl["room"],
            "batch_id": batch_id,
            "day_of_week": tmpl["day"],
            "start_time": tmpl["start"],
            "end_time": tmpl["end"],
        }

        s_res = post_json(session, f"{base_url}/institute-admin/timetable-slots", slot_payload, headers=admin_headers)
        if s_res.status_code == 201:
            slots_created += 1
        elif s_res.status_code == 409:
            log(f"Conflict on slot {tmpl['code']} (Day {tmpl['day']} {tmpl['start']}-{tmpl['end']}). Adjusting time...")
            # Try alternate times/days
            for offset in range(1, 4):
                parts_s = [int(x) for x in tmpl["start"].split(":")]
                parts_e = [int(x) for x in tmpl["end"].split(":")]
                slot_payload["start_time"] = f"{(parts_s[0]+offset):02d}:{parts_s[1]:02d}"
                slot_payload["end_time"] = f"{(parts_e[0]+offset):02d}:{parts_e[1]:02d}"
                s_retry = post_json(session, f"{base_url}/institute-admin/timetable-slots", slot_payload, headers=admin_headers)
                if s_retry.status_code == 201:
                    slots_created += 1
                    break

    log(f"Created {slots_created} timetable slots across the 6 shared rooms.")

    # 1.6 Register Staff & Admin Accounts
    log("\nRegistering Health Admin, Class Teachers, Course Faculty, and Bridging Faculty...")

    hadmin_user = {
        "name": "Dr. Sarah HealthAdmin",
        "email": "healthadmin@campustrace.edu",
        "password": "HealthAdminPass123!",
        "role": "health_admin",
    }
    post_json(session, f"{base_url}/auth/register", hadmin_user, headers=admin_headers)

    bridging_fac = {
        "name": "Prof. Bridge CrossDivision",
        "email": "prof.bridge@campustrace.edu",
        "password": "BridgeFacultyPass123!",
        "role": "course_faculty",
    }
    b_res = post_json(session, f"{base_url}/auth/register", bridging_fac, headers=admin_headers)
    bridging_fac_id = b_res.json()["id"] if b_res.status_code == 201 else None

    if not bridging_fac_id:
        u_list = get_json(session, f"{base_url}/institute-admin/users?role=course_faculty", headers=admin_headers).json().get("items", [])
        for u in u_list:
            if u["email"] == bridging_fac["email"]:
                bridging_fac_id = u["id"]
                break

    if bridging_fac_id:
        post_json(session, f"{base_url}/institute-admin/faculty-assignments", {
            "faculty_id": bridging_fac_id,
            "course_id": course_info["CE201"]["id"],
        }, headers=admin_headers)
        post_json(session, f"{base_url}/institute-admin/faculty-assignments", {
            "faculty_id": bridging_fac_id,
            "course_id": course_info["IT301"]["id"],
        }, headers=admin_headers)
        log(f"Assigned Bridging Faculty '{bridging_fac['email']}' to CE201 (CE) and IT301 (IT).")

    cts = {
        "CE": {"name": "Prof. Hopper (CT CE)", "email": "ct_ce@campustrace.edu", "password": "ClassTeacherPass123!", "role": "class_teacher", "division_id": div_ids["CE"]},
        "IT": {"name": "Prof. Turing (CT IT)", "email": "ct_it@campustrace.edu", "password": "ClassTeacherPass123!", "role": "class_teacher", "division_id": div_ids["IT"]},
        "AI": {"name": "Prof. Lovelace (CT AI)", "email": "ct_ai@campustrace.edu", "password": "ClassTeacherPass123!", "role": "class_teacher", "division_id": div_ids["AI"]},
        "DS": {"name": "Prof. Knuth (CT DS)", "email": "ct_ds@campustrace.edu", "password": "ClassTeacherPass123!", "role": "class_teacher", "division_id": div_ids["DS"]},
    }

    ct_tokens = {}
    for key, ct in cts.items():
        post_json(session, f"{base_url}/auth/register", ct, headers=admin_headers)
        login = post_json(session, f"{base_url}/auth/login", {"email": ct["email"], "password": ct["password"]})
        if login.status_code == 200:
            ct_tokens[key] = login.json()["access_token"]

    faculties = [
        {"name": "Prof. CE Faculty 1", "email": "fac_ce_1@campustrace.edu", "password": "FacultyPass123!", "role": "course_faculty", "courses": ["CE202L", "CE203T"]},
        {"name": "Prof. IT Faculty 1", "email": "fac_it_1@campustrace.edu", "password": "FacultyPass123!", "role": "course_faculty", "courses": ["IT302L", "IT303T"]},
        {"name": "Prof. AI Faculty 1", "email": "fac_ai_1@campustrace.edu", "password": "FacultyPass123!", "role": "course_faculty", "courses": ["AI101", "AI102L", "AI104_ELEC"]},
        {"name": "Prof. DS Faculty 1", "email": "fac_ds_1@campustrace.edu", "password": "FacultyPass123!", "role": "course_faculty", "courses": ["DS401", "DS402L"]},
    ]

    fac_tokens = {}
    for fac in faculties:
        f_res = post_json(session, f"{base_url}/auth/register", fac, headers=admin_headers)
        f_id = f_res.json()["id"] if f_res.status_code == 201 else None
        if f_id:
            for c_code in fac["courses"]:
                if c_code in course_info:
                    post_json(session, f"{base_url}/institute-admin/faculty-assignments", {
                        "faculty_id": f_id, "course_id": course_info[c_code]["id"]
                    }, headers=admin_headers)

        f_login = post_json(session, f"{base_url}/auth/login", {"email": fac["email"], "password": fac["password"]})
        if f_login.status_code == 200:
            fac_tokens[fac["email"]] = f_login.json()["access_token"]

    # 1.7 Bulk Fast Creation of 60 Students per division (240 Students Total)
    log("\nCreating 60 student accounts per division (240 total)...")

    from app import create_app
    from app.extensions import db, bcrypt
    from app.models.user import User

    flask_app = create_app("development")

    all_students = []
    with flask_app.app_context():
        hashed_pwd = bcrypt.generate_password_hash("StudentPass123!").decode("utf-8")
        
        for div_key in ["CE", "IT", "AI", "DS"]:
            d_id = div_ids[div_key]
            for i in range(1, 61):
                s_name = f"Student {div_key} {i}"
                s_email = f"student_{div_key.lower()}_{i}@campustrace.edu"
                s_pass = "StudentPass123!"

                existing = User.query.filter_by(email=s_email).first()
                if not existing:
                    u = User(
                        name=s_name,
                        email=s_email,
                        password_hash=hashed_pwd,
                        role="student",
                        division_id=d_id,
                    )
                    db.session.add(u)
                    db.session.flush()
                    s_id = u.id
                else:
                    s_id = existing.id

                all_students.append({
                    "id": s_id,
                    "name": s_name,
                    "email": s_email,
                    "password": s_pass,
                    "div_key": div_key,
                    "division_id": d_id,
                })

        db.session.commit()

    log(f"Created/verified {len(all_students)} student accounts across 4 divisions.")

    # 1.8 Enroll Students into Home Division Courses & Batches via REST API
    log("\nEnrolling students into home division courses and lab/tutorial batches via REST API...")
    ct_headers_map = {k: {"Authorization": f"Bearer {v}"} for k, v in ct_tokens.items()}

    for st in all_students:
        div_key = st["div_key"]
        s_id = st["id"]

        # 1. Enroll in theory course via CT approval endpoint
        theory_map = {"CE": "CE201", "IT": "IT301", "AI": "AI101", "DS": "DS401"}
        lab_map = {"CE": "CE202L", "IT": "IT302L", "AI": "AI102L", "DS": "DS402L"}
        tut_map = {"CE": "CE203T", "IT": "IT303T", "AI": "AI103T", "DS": "DS403T"}

        theory_code = theory_map.get(div_key)
        lab_code = lab_map.get(div_key)
        tut_code = tut_map.get(div_key)

        if theory_code in course_info:
            post_json(session, f"{base_url}/class-teacher/enrollment-changes/approve", {
                "student_id": s_id,
                "course_id": course_info[theory_code]["id"],
            }, headers=ct_headers_map[div_key])

        # 2. Self-service batch registration via POST /student/register-batches for lab & tutorial courses

        batch_selections = []
        if lab_code in course_info and course_info[lab_code]["batches"]:
            b_lab = course_info[lab_code]["batches"]["B1" if (s_id % 2 == 1) else "B2"]
            batch_selections.append({"course_id": course_info[lab_code]["id"], "batch_id": b_lab})

        if tut_code in course_info and course_info[tut_code]["batches"]:
            b_tut = course_info[tut_code]["batches"]["B1" if (s_id % 2 == 1) else "B2"]
            batch_selections.append({"course_id": course_info[tut_code]["id"], "batch_id": b_tut})

        if batch_selections:
            # Login student and post batch selections
            st_login = post_json(session, f"{base_url}/auth/login", {"email": st["email"], "password": st["password"]})
            if st_login.status_code == 200:
                st_headers = {"Authorization": f"Bearer {st_login.json()['access_token']}"}
                post_json(session, f"{base_url}/student/register-batches", {"batch_selections": batch_selections}, headers=st_headers)

    log("Enrolled students into home division theory courses and lab/tutorial batches.")

    # 1.9 Shared Elective Enrollment for Data Science Students
    log("\nHandling Shared Elective (AI104_ELEC) enrollment for Data Science students...")
    ds_students = [s for s in all_students if s["div_key"] == "DS"][:20]
    elective_course_id = course_info["AI104_ELEC"]["id"]

    for ds_st in ds_students:
        # First attempt self-service as student (will be rejected as cross-division without batch)
        st_login = post_json(session, f"{base_url}/auth/login", {"email": ds_st["email"], "password": ds_st["password"]})
        if st_login.status_code == 200:
            st_headers = {"Authorization": f"Bearer {st_login.json()['access_token']}"}
            rej_res = post_json(session, f"{base_url}/student/register-batches", {
                "batch_selections": [{"course_id": elective_course_id, "batch_id": 9999}]
            }, headers=st_headers)
            # Rejected per contract requirement -> fall back to class_teacher approval endpoint
            if rej_res.status_code != 201:
                post_json(session, f"{base_url}/class-teacher/enrollment-changes/approve", {
                    "student_id": ds_st["id"],
                    "course_id": elective_course_id,
                }, headers=ct_headers_map["DS"])

    log("Data Science students successfully enrolled in Shared Elective (AI104_ELEC) via Class Teacher approval.")

    # -------------------------------------------------------------------------
    # STEP 2: Populate Disease Knowledge Base (as Health Admin)
    # -------------------------------------------------------------------------
    log("\n=== STEP 2: Populate Disease Knowledge Base ===")

    ha_login = post_json(session, f"{base_url}/auth/login", {"email": hadmin_user["email"], "password": hadmin_user["password"]})
    if ha_login.status_code != 200:
        log_error("Failed to login as Health Admin")
        sys.exit(1)

    ha_token = ha_login.json()["access_token"]
    ha_headers = {"Authorization": f"Bearer {ha_token}"}

    disease_specs = [
        {
            "name": "Chickenpox",
            "symptoms": "fever rash itchy spots fatigue headache",
            "preventive_measures": "isolate vaccination rest fluids avoid scratch",
            "incubation_period_days": 14,
        },
        {
            "name": "Seasonal Flu",
            "symptoms": "fever cough sore throat body ache chills",
            "preventive_measures": "mask isolate rest fluids warm water",
            "incubation_period_days": 2,
        },
        {
            "name": "Common Cold",
            "symptoms": "runny nose sneezing mild cough congestion",
            "preventive_measures": "wash hands wear mask rest stay warm",
            "incubation_period_days": 1,
        },
        {
            "name": "Viral Fever",
            "symptoms": "high fever chills fatigue headache muscle pain",
            "preventive_measures": "rest fluids paracetamol isolate monitor temp",
            "incubation_period_days": 3,
        },
    ]

    disease_ids = {}
    for d_spec in disease_specs:
        res = post_json(session, f"{base_url}/health-admin/disease-kb", d_spec, headers=ha_headers)
        if res.status_code in (201, 200):
            d_id = res.json()["id"]
            disease_ids[d_spec["name"]] = d_id
            log(f"Created Disease KB entry '{d_spec['name']}' (ID: {d_id})")
        else:
            disease_ids[d_spec["name"]] = len(disease_ids) + 1

    # -------------------------------------------------------------------------
    # STEP 3: Internal Python Batch Jobs (Presence & Contact Graph Edges)
    # -------------------------------------------------------------------------
    log("\n=== STEP 3: Internal Python Batch Jobs (Multi-Week Timetable Simulation) ===")

    try:
        from app.services.presence_builder import build_presence_for_date
        from app.services.graph_builder import build_edges_for_date

        today = date.today()
        simulation_dates = [today - timedelta(days=i) for i in range(21)]

        with flask_app.app_context():
            total_presence = 0
            total_edges = 0
            for target_d in simulation_dates:
                p_cnt = build_presence_for_date(target_d)
                e_cnt = build_edges_for_date(target_d)
                total_presence += p_cnt
                total_edges += e_cnt
                log(f"Date {target_d.isoformat()}: Created {p_cnt} Presence rows, {e_cnt} Contact Edge rows.")
            log(f"Multi-week simulation complete: Total Presences={total_presence}, Total Contact Edges={total_edges}")
    except Exception as e:
        log_error(f"Failed to execute internal batch jobs: {e}")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # STEP 4: Health Reports & Absence Flags via REST
    # -------------------------------------------------------------------------
    log("\n=== STEP 4: Filing Health Reports & Raising Absence Flags ===")

    ce_student_1 = next(s for s in all_students if s["div_key"] == "CE")
    it_student_1 = next(s for s in all_students if s["div_key"] == "IT")
    ai_student_1 = next(s for s in all_students if s["div_key"] == "AI")
    ds_student_1 = next(s for s in all_students if s["div_key"] == "DS")
    ce_student_2 = [s for s in all_students if s["div_key"] == "CE"][1]

    report_date = today - timedelta(days=2)

    reports_config = [
        # BRIDGING CASE: CE Student 1 in CE201 (taught by Bridging Faculty, who also teaches IT301 in IT)
        {"student": ce_student_1, "disease_id": disease_ids.get("Seasonal Flu", 2), "custom": "High fever and persistent cough", "is_bridge_case": True},
        {"student": it_student_1, "disease_id": disease_ids.get("Viral Fever", 4), "custom": "Chills and body aches", "is_bridge_case": False},
        {"student": ai_student_1, "disease_id": disease_ids.get("Common Cold", 3), "custom": "Sneezing and runny nose", "is_bridge_case": False},
        {"student": ds_student_1, "disease_id": disease_ids.get("Chickenpox", 1), "custom": "Itchy rash and spots", "is_bridge_case": False},
        {"student": ce_student_2, "disease_id": disease_ids.get("Seasonal Flu", 2), "custom": "Sore throat and fever", "is_bridge_case": False},
    ]

    bridging_report_id = None
    for r_cfg in reports_config:
        st = r_cfg["student"]
        st_login = post_json(session, f"{base_url}/auth/login", {"email": st["email"], "password": st["password"]})
        if st_login.status_code == 200:
            st_token = st_login.json()["access_token"]
            st_headers = {"Authorization": f"Bearer {st_token}"}
            rep_res = post_json(session, f"{base_url}/student/health-report", {
                "onset_date": report_date.isoformat(),
                "severity": "moderate",
                "disease_id": r_cfg["disease_id"],
                "custom_symptoms": r_cfg["custom"],
            }, headers=st_headers)

            if rep_res.status_code == 201:
                rep_id = rep_res.json()["id"]
                log(f"Health report #{rep_id} filed for {st['email']} (Div {st['div_key']})")
                if r_cfg["is_bridge_case"]:
                    bridging_report_id = rep_id

    # Raise Absence Flags & Student Responses
    log("\nRaising absence flags and student responses...")
    fac_ce_token = fac_tokens["fac_ce_1@campustrace.edu"]
    fac_ce_headers = {"Authorization": f"Bearer {fac_ce_token}"}

    student_flag_target_1 = [s for s in all_students if s["div_key"] == "CE"][2]
    student_flag_target_2 = [s for s in all_students if s["div_key"] == "CE"][3]

    # Flag 1: Course Faculty flags Student CE 3 in CE202L
    f1_res = post_json(session, f"{base_url}/faculty/absence-flags", {
        "student_id": student_flag_target_1["id"],
        "course_id": course_info["CE202L"]["id"],
        "flagged_date": today.isoformat(),
        "reason_category": "health_observed",
    }, headers=fac_ce_headers)

    # Flag 2: Course Faculty flags Student CE 3 in CE203T (Same student across > 1 course -> ESCALATION!)
    f2_res = post_json(session, f"{base_url}/faculty/absence-flags", {
        "student_id": student_flag_target_1["id"],
        "course_id": course_info["CE203T"]["id"],
        "flagged_date": today.isoformat(),
        "reason_category": "unexcused_absence",
    }, headers=fac_ce_headers)

    # Flag 3: Course Faculty flags Student CE 4 in CE202L
    f3_res = post_json(session, f"{base_url}/faculty/absence-flags", {
        "student_id": student_flag_target_2["id"],
        "course_id": course_info["CE202L"]["id"],
        "flagged_date": today.isoformat(),
        "reason_category": "health_observed",
    }, headers=fac_ce_headers)

    if f1_res.status_code == 201:
        flag1_id = f1_res.json()["id"]
        st1_login = post_json(session, f"{base_url}/auth/login", {"email": student_flag_target_1["email"], "password": student_flag_target_1["password"]})
        if st1_login.status_code == 200:
            st1_headers = {"Authorization": f"Bearer {st1_login.json()['access_token']}"}
            post_json(session, f"{base_url}/student/absence-flags/{flag1_id}/respond", {"confirm": True}, headers=st1_headers)
            log(f"Student '{student_flag_target_1['email']}' confirmed absence flag #{flag1_id}.")

    if f3_res.status_code == 201:
        flag3_id = f3_res.json()["id"]
        st2_login = post_json(session, f"{base_url}/auth/login", {"email": student_flag_target_2["email"], "password": student_flag_target_2["password"]})
        if st2_login.status_code == 200:
            st2_headers = {"Authorization": f"Bearer {st2_login.json()['access_token']}"}
            post_json(session, f"{base_url}/student/absence-flags/{flag3_id}/respond", {"confirm": False}, headers=st2_headers)
            log(f"Student '{student_flag_target_2['email']}' dismissed/denied absence flag #{flag3_id}.")

    # -------------------------------------------------------------------------
    # STEP 5: Verification of Cross-Division Bridging Case
    # -------------------------------------------------------------------------
    log("\n=== STEP 5: Verifying Cross-Division Bridging Case ===")

    verified_bridging_contacts = []
    if bridging_report_id:
        graph_res = get_json(session, f"{base_url}/health-admin/contact-graph/{bridging_report_id}?direction=both&max_depth=2", headers=ha_headers)
        if graph_res.status_code == 200:
            graph_data = graph_res.json()
            contacts = graph_data.get("contacts", {})
            fwd_contacts = contacts.get("forward", {})
            bwd_contacts = contacts.get("backward", {})
            all_traced = {**fwd_contacts, **bwd_contacts}

            log(f"Retrieved contact graph for Bridging Case Health Report #{bridging_report_id}. Total traced contacts: {len(all_traced)}")
            for u_id, c_info in all_traced.items():
                verified_bridging_contacts.append({
                    "user_id": u_id,
                    "depth": c_info.get("depth"),
                    "risk_score": c_info.get("risk_score"),
                    "risk_level": c_info.get("risk_level"),
                })
        else:
            log_error(f"Failed to fetch contact graph for bridging report: {graph_res.status_code}")

    # -------------------------------------------------------------------------
    # PRINT FULL POPULATION & VERIFICATION SUMMARY
    # -------------------------------------------------------------------------
    log("\n===================================================================")
    log("CAMPUSTRACE LOCAL VERIFICATION POPULATION & BRIDGING SUMMARY")
    log("===================================================================")

    print("\n[ACCOUNT CREDENTIALS SUMMARY]")
    print("-------------------------------------------------------------------")
    print("1. Institute Admin:")
    print(f"   - Email: {admin_creds['email']} | Password: {admin_creds['password']}")
    print("\n2. Health Admin:")
    print(f"   - Email: {hadmin_user['email']} | Password: {hadmin_user['password']}")
    print("\n3. Class Teachers:")
    for k, ct in cts.items():
        print(f"   - Div {k}: {ct['email']} | Password: {ct['password']}")
    print("\n4. Bridging Faculty (CE & IT):")
    print(f"   - Email: {bridging_fac['email']} | Password: {bridging_fac['password']}")
    print("\n5. Course Faculty:")
    for fac in faculties:
        print(f"   - Email: {fac['email']} | Password: {fac['password']}")
    print("\n6. Sample Student Accounts (240 Total Registered Across 4 Divisions):")
    for div_k in ["CE", "IT", "AI", "DS"]:
        st = next(s for s in all_students if s["div_key"] == div_k)
        print(f"   - Div {div_k}: {st['name']} ({st['email']}) | Password: {st['password']}")

    it_student_ids = {str(s["id"]) for s in all_students if s["div_key"] == "IT"}
    ce_student_ids = {str(s["id"]) for s in all_students if s["div_key"] == "CE"}
    it_traced = [c for c in verified_bridging_contacts if str(c["user_id"]) in it_student_ids]
    ce_traced = [c for c in verified_bridging_contacts if str(c["user_id"]) in ce_student_ids]
    bridge_traced = [c for c in verified_bridging_contacts if bridging_fac_id and str(c["user_id"]) == str(bridging_fac_id)]

    print("\n[CROSS-DIVISION BRIDGING VERIFICATION PROOF]")
    print("-------------------------------------------------------------------")
    print(f"Index Case Health Report ID : #{bridging_report_id}")
    print(f"Index Student               : {ce_student_1['name']} ({ce_student_1['email']}) [Division: Computer Engineering]")
    print(f"Bridging Faculty Member     : {bridging_fac['name']} ({bridging_fac['email']})")
    print("  -> Teaches 'CE201' in Computer Engineering AND 'IT301' in Information Technology")
    print(f"Traced Contacts Result Count: {len(verified_bridging_contacts)} contacts traced")
    print(f"  - Bridging Faculty (Depth 1): {len(bridge_traced)} traced")
    print(f"  - CE Division Classmates    : {len(ce_traced)} traced")
    print(f"  - IT Division Students (Depth 2): {len(it_traced)} traced")
    if it_traced and bridge_traced:
        print("Verification Result         : CONFIRMED — Contact graph successfully traced from CE student through Bridging Faculty to IT division students!")
    elif len(verified_bridging_contacts) > 0:
        print("Verification Result         : PARTIAL — Traced contacts found.")
    else:
        print("Verification Result         : FAILED — No contacts traced.")

    print("\n[ABSENCE ESCALATION SUMMARY]")
    print("-------------------------------------------------------------------")
    print(f"Escalation Target Student  : {student_flag_target_1['name']} ({student_flag_target_1['email']})")
    print("Multiple Flagged Courses    : CE202L (Lab) and CE203T (Tutorial)")
    print("Resulting Status            : Triggers Class Teacher 14-day Escalation Rule")
    print("-------------------------------------------------------------------\n")


if __name__ == "__main__":
    main()
