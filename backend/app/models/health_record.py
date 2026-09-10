from app.extensions import db

SEVERITY_LEVELS = ("mild", "moderate", "severe")
HEALTH_STATUSES = ("reported", "confirmed", "recovered")


class HealthRecord(db.Model):
    __tablename__ = "health_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    disease_id = db.Column(db.Integer, db.ForeignKey("disease_kb.id", ondelete="SET NULL"), nullable=True)
    custom_symptoms = db.Column(db.Text, nullable=True)
    onset_date = db.Column(db.Date, nullable=False)
    severity = db.Column(db.Enum(*SEVERITY_LEVELS, name="severity_enum"), nullable=False)
    status = db.Column(db.Enum(*HEALTH_STATUSES, name="health_status_enum"), nullable=False, default="reported")
    reported_at = db.Column(db.DateTime, server_default=db.func.now())
    confirmed_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])
    disease = db.relationship("DiseaseKB")

    __table_args__ = (db.Index("idx_health_status_date", "status", "onset_date"),)

    def __repr__(self):
        return f"<HealthRecord user={self.user_id} status={self.status}>"