from app.extensions import db

TRACING_DIRECTIONS = ("forward", "backward", "both")


class SystemConfig(db.Model):
    """Singleton row (id is always 1) — Institute Admin's global settings.
    Use SystemConfig.get() rather than querying directly, so callers
    don't need to know about the singleton convention."""

    __tablename__ = "system_config"

    id = db.Column(db.SmallInteger, primary_key=True, default=1)
    k_anonymity_threshold = db.Column(db.SmallInteger, nullable=False, default=5)
    default_tracing_depth = db.Column(db.SmallInteger, nullable=False, default=2)
    default_tracing_direction = db.Column(db.Enum(*TRACING_DIRECTIONS, name="tracing_direction_enum"), nullable=False, default="both")
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (db.CheckConstraint("id = 1", name="chk_single_row"),)

    @classmethod
    def get(cls) -> "SystemConfig":
        config = cls.query.get(1)
        if config is None:
            config = cls(id=1)
            db.session.add(config)
            db.session.commit()
        return config

    def __repr__(self):
        return f"<SystemConfig k={self.k_anonymity_threshold} depth={self.default_tracing_depth}>"