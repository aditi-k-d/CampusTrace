from app.extensions import db

ABSENCE_STATES = ("pending", "confirmed", "dismissed")


class AbsenceFlag(db.Model):
    __tablename__ = "absence_flags"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    flagged_date = db.Column(db.Date, nullable=False)
    reason_category = db.Column(db.String(100), nullable=False)  # category, never a diagnosis
    state = db.Column(db.Enum(*ABSENCE_STATES, name="absence_state_enum"), nullable=False, default="pending", index=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    student = db.relationship("User", foreign_keys=[student_id])
    faculty = db.relationship("User", foreign_keys=[faculty_id])
    course = db.relationship("Course")

    def __repr__(self):
        return f"<AbsenceFlag student={self.student_id} state={self.state}>"