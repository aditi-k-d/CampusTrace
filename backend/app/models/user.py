from app.extensions import db, bcrypt

ROLE_STUDENT = "student"
ROLE_COURSE_FACULTY = "course_faculty"
ROLE_CLASS_TEACHER = "class_teacher"
ROLE_HEALTH_ADMIN = "health_admin"
ROLE_INSTITUTE_ADMIN = "institute_admin"

ROLES = (ROLE_STUDENT, ROLE_COURSE_FACULTY, ROLE_CLASS_TEACHER, ROLE_HEALTH_ADMIN, ROLE_INSTITUTE_ADMIN)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(*ROLES, name="user_role_enum"), nullable=False, index=True)

    # Meaningful for students and class_teacher. Faculty span divisions via
    # FacultyCourseAssignment instead, so this stays NULL for them.
    division_id = db.Column(db.Integer, db.ForeignKey("divisions.id", ondelete="SET NULL"), nullable=True, index=True)

    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    division = db.relationship("Division", back_populates="users")
    faculty_assignments = db.relationship("FacultyCourseAssignment", back_populates="faculty", cascade="all, delete-orphan")
    enrollments = db.relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")

    # --- password handling ---

    def set_password(self, plaintext: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(plaintext).decode("utf-8")

    def check_password(self, plaintext: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, plaintext)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"