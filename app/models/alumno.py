from app.extensions import db
from app.models.mixins import TimestampMixin

class Alumno(TimestampMixin, db.Model):
    __tablename__ = "alumnos"

    id = db.Column(db.Integer, primary_key=True)

    # Multi-tenant
    academia_id = db.Column(db.Integer, db.ForeignKey("academias.id"), nullable=False, index=True)

    nombres = db.Column(db.String(120), nullable=False)
    apellidos = db.Column(db.String(120), nullable=False)

    documento = db.Column(db.String(50), nullable=True)  # cédula/pasaporte opcional
    cinturon = db.Column(db.String(50), nullable=True)   # ej: "Amarillo", "Rojo punta negra", etc.

    activo = db.Column(db.Boolean, default=True, nullable=False)

    __table_args__ = (
        db.Index("ix_alumnos_academia_apellidos", "academia_id", "apellidos"),
    )

    @property
    def nombre_completo(self) -> str:
        return f"{self.apellidos} {self.nombres}".strip()

    def __repr__(self) -> str:
        return f"<Alumno {self.id} {self.nombre_completo}>"