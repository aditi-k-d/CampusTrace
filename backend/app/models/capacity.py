from app.extensions import db


class Capacity(db.Model):
    __tablename__ = "capacity"

    id = db.Column(db.Integer, primary_key=True)
    facility_name = db.Column(db.String(100), nullable=False)
    total_beds = db.Column(db.SmallInteger, nullable=False)
    occupied_beds = db.Column(db.SmallInteger, nullable=False, default=0)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f"<Capacity {self.facility_name} {self.occupied_beds}/{self.total_beds}>"


class IsolationAllocation(db.Model):
    __tablename__ = "isolation_allocations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    capacity_id = db.Column(db.Integer, db.ForeignKey("capacity.id", ondelete="CASCADE"), nullable=False)
    priority_score = db.Column(db.Numeric(5, 2), nullable=False)  # from priority_queue.py at allocation time
    allocated_at = db.Column(db.DateTime, server_default=db.func.now())
    released_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User")
    capacity = db.relationship("Capacity")

    __table_args__ = (db.Index("idx_isolation_active", "capacity_id", "released_at"),)

    def __repr__(self):
        return f"<IsolationAllocation user={self.user_id} capacity={self.capacity_id}>"