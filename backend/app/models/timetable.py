from app.extensions import db


class TimetableSlot(db.Model):
    __tablename__ = "timetable_slots"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id", ondelete="CASCADE"), nullable=True)
    day_of_week = db.Column(db.SmallInteger, nullable=False)  # 0=Mon .. 6=Sun
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    course = db.relationship("Course", back_populates="timetable_slots")
    room = db.relationship("Room")
    batch = db.relationship("Batch")

    __table_args__ = (db.Index("idx_slot_room_day", "room_id", "day_of_week"),)

    def __repr__(self):
        return f"<TimetableSlot course={self.course_id} room={self.room_id} day={self.day_of_week}>"