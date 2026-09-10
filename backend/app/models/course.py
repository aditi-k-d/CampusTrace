from app.extensions import db


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    division_id = db.Column(db.Integer, db.ForeignKey("divisions.id", ondelete="CASCADE"), nullable=False, index=True)
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    course_type = db.Column(db.Enum("theory", "lab", "tutorial", name="course_type_enum"), nullable=False)

    division = db.relationship("Division", back_populates="courses")
    batches = db.relationship("Batch", back_populates="course", cascade="all, delete-orphan")
    timetable_slots = db.relationship("TimetableSlot", back_populates="course", cascade="all, delete-orphan")
    enrollments = db.relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    faculty_assignments = db.relationship("FacultyCourseAssignment", back_populates="course", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Course {self.code}>"


class Batch(db.Model):
    __tablename__ = "batches"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(20), nullable=False)  # e.g. 'B1'

    course = db.relationship("Course", back_populates="batches")

    __table_args__ = (db.UniqueConstraint("course_id", "name", name="uq_batch_course_name"),)

    def __repr__(self):
        return f"<Batch {self.name} of course {self.course_id}>"


class FacultyCourseAssignment(db.Model):
    """Faculty <-> course link. Deliberately separate from Enrollment so a
    faculty member teaching courses in two different divisions (the
    Phase 2 cross-division bridging case) is a plain query here, not a
    special case bolted onto student enrollment."""

    __tablename__ = "faculty_course_assignments"

    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)

    faculty = db.relationship("User", back_populates="faculty_assignments")
    course = db.relationship("Course", back_populates="faculty_assignments")

    __table_args__ = (db.UniqueConstraint("faculty_id", "course_id", name="uq_faculty_course"),)