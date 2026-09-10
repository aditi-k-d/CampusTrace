from app.extensions import db


class ContactEdge(db.Model):
    """One row per (pair, date, room) contact occurrence — kept
    per-occurrence rather than pre-aggregated so risk_engine.py has
    duration + room-type-weight per contact to apply the decay/weighting
    formula against, rather than a single already-collapsed number."""

    __tablename__ = "contact_edges"

    id = db.Column(db.BigInteger, primary_key=True)
    user_a_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_b_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    contact_date = db.Column(db.Date, nullable=False)
    duration_minutes = db.Column(db.SmallInteger, nullable=False)
    room_type_weight = db.Column(db.Numeric(4, 3), nullable=False, default=1.000)

    user_a = db.relationship("User", foreign_keys=[user_a_id])
    user_b = db.relationship("User", foreign_keys=[user_b_id])
    room = db.relationship("Room")

    __table_args__ = (
        db.UniqueConstraint("user_a_id", "user_b_id", "contact_date", "room_id", name="uq_edge"),
        # One index per traversal direction — BFS/DFS will hit whichever
        # side matches the node it's currently expanding from.
        db.Index("idx_edge_a_date", "user_a_id", "contact_date"),
        db.Index("idx_edge_b_date", "user_b_id", "contact_date"),
    )

    def __repr__(self):
        return f"<ContactEdge {self.user_a_id}<->{self.user_b_id} on {self.contact_date}>"