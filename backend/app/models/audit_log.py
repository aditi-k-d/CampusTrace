from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # e.g. 'view_contact_graph', 'edit_disease_kb'
    target_type = db.Column(db.String(50), nullable=True)
    target_id = db.Column(db.BigInteger, nullable=True)
    details = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User")

    __table_args__ = (
        # Audit log grows unbounded — the institute_admin viewer always
        # filters by actor or by action, both within a date range.
        db.Index("idx_audit_user_date", "user_id", "created_at"),
        db.Index("idx_audit_action_date", "action", "created_at"),
    )

    def __repr__(self):
        return f"<AuditLog {self.action} by user={self.user_id}>"