from app.extensions import db
from app.models.mixins import TimestampMixin

class EvaluacionItem(TimestampMixin, db.Model):
    __tablename__ = "evaluacion_items"

    id = db.Column(db.Integer, primary_key=True)

    evaluacion_id = db.Column(db.Integer, db.ForeignKey("evaluaciones.id"), nullable=False, index=True)

    criterio_codigo = db.Column(db.String(50), nullable=False)
    criterio_nombre = db.Column(db.String(120), nullable=False)

    puntaje = db.Column(db.Numeric(6, 2), default=0, nullable=False)
    max_puntaje = db.Column(db.Numeric(6, 2), default=0, nullable=False)

    notas = db.Column(db.String(255), nullable=True)