from app.extensions import db

RISK_LEVELS = ("low", "medium", "high")


class Alert(db.Model):
    __tablename__ = "alerts"

    # BigInteger for MySQL/production headroom on a high-volume table;
    # .with_variant(Integer, "sqlite") keeps autoincrement working when
    # testing locally against SQLite, which only auto-increments a
    # plain INTEGER primary key, not BIGINT.
    id = db.Column(db.BigInteger().with_variant(db.Integer, "sqlite"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_health_record_id = db.Column(db.Integer, db.ForeignKey("health_records.id", ondelete="CASCADE"), nullable=False)
    risk_level = db.Column(db.Enum(*RISK_LEVELS, name="risk_level_enum"), nullable=False)
    risk_score = db.Column(db.Numeric(5, 2), nullable=False)
    # Denormalized snapshots so an alert's content survives later KB edits.
    symptoms_snapshot = db.Column(db.Text, nullable=False)
    precautions_snapshot = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), index=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User")
    source_health_record = db.relationship("HealthRecord")

    def __repr__(self):
        return f"<Alert user={self.user_id} risk={self.risk_level}>"