from app.extensions import db


class Enrollment(db.Model):
    __tablename__ = "enrollments"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    # NULL for theory courses — only lab/tutorial courses need a batch pick.
    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id", ondelete="SET NULL"), nullable=True, index=True)

    student = db.relationship("User", back_populates="enrollments")
    course = db.relationship("Course", back_populates="enrollments")
    batch = db.relationship("Batch")

    __table_args__ = (db.UniqueConstraint("student_id", "course_id", name="uq_enrollment"),)

    def __repr__(self):
        return f"<Enrollment student={self.student_id} course={self.course_id}>"