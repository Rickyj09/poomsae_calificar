from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, login_manager
from app.models.mixins import TimestampMixin

class User(TimestampMixin, UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    academia_id = db.Column(db.Integer, db.ForeignKey("academias.id"), nullable=False, index=True)

    email = db.Column(db.String(190), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    rol = db.Column(db.Enum("admin", "coach", "judge", "student", name="user_roles"),
                    default="admin", nullable=False)

    activo = db.Column(db.Boolean, default=True, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("academia_id", "email", name="uq_user_academia_email"),
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))