from app.extensions import db
from app.models.mixins import TimestampMixin

class Academia(TimestampMixin, db.Model):
    __tablename__ = "academias"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Academia {self.slug}>"