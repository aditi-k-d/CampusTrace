from app.extensions import db


class Division(db.Model):
    __tablename__ = "divisions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    branch = db.Column(db.String(100), nullable=False)
    year = db.Column(db.SmallInteger, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    courses = db.relationship("Course", back_populates="division", cascade="all, delete-orphan")
    users = db.relationship("User", back_populates="division")

    def __repr__(self):
        return f"<Division {self.name}>"


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    building = db.Column(db.String(100))
    capacity = db.Column(db.SmallInteger)

    __table_args__ = (db.UniqueConstraint("name", "building", name="uq_room_name_building"),)

    def __repr__(self):
        return f"<Room {self.name}>"