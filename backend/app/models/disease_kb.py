from app.extensions import db


class DiseaseKB(db.Model):
    __tablename__ = "disease_kb"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    symptoms = db.Column(db.Text, nullable=False)
    preventive_measures = db.Column(db.Text, nullable=False)
    incubation_period_days = db.Column(db.SmallInteger)

    added_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f"<DiseaseKB {self.name}>"