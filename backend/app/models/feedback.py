from app.extensions import db


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.BigInteger, db.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, unique=True)
    is_false_positive = db.Column(db.Boolean, nullable=False)
    submitted_at = db.Column(db.DateTime, server_default=db.func.now())
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    weight_adjusted = db.Column(db.Boolean, nullable=False, default=False)

    alert = db.relationship("Alert")
    reviewer = db.relationship("User")

    def __repr__(self):
        return f"<Feedback alert={self.alert_id} false_positive={self.is_false_positive}>"