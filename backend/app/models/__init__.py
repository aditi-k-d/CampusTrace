"""
Importing this package pulls in every model so SQLAlchemy's metadata
is complete — needed for db.create_all() in dev/tests and for
Alembic's autogenerate to see every table.
"""

from app.models.division import Division, Room
from app.models.course import Course, Batch, FacultyCourseAssignment
from app.models.user import User
from app.models.enrollment import Enrollment
from app.models.timetable import TimetableSlot
from app.models.presence import Presence
from app.models.contact_edge import ContactEdge
from app.models.disease_kb import DiseaseKB
from app.models.health_record import HealthRecord
from app.models.absence_flag import AbsenceFlag
from app.models.alert import Alert
from app.models.feedback import Feedback
from app.models.capacity import Capacity, IsolationAllocation
from app.models.system_config import SystemConfig
from app.models.audit_log import AuditLog

__all__ = [
    "Division", "Room",
    "Course", "Batch", "FacultyCourseAssignment",
    "User",
    "Enrollment",
    "TimetableSlot",
    "Presence",
    "ContactEdge",
    "DiseaseKB",
    "HealthRecord",
    "AbsenceFlag",
    "Alert",
    "Feedback",
    "Capacity", "IsolationAllocation",
    "SystemConfig",
    "AuditLog",
]