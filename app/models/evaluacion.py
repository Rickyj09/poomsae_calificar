from app.extensions import db
from app.models.mixins import TimestampMixin

class Evaluacion(TimestampMixin, db.Model):
    __tablename__ = "evaluaciones"

    id = db.Column(db.Integer, primary_key=True)

    academia_id = db.Column(db.Integer, db.ForeignKey("academias.id"), nullable=False, index=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False, index=True)
    juez_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    tipo = db.Column(db.String(20), default="manual", nullable=False)   # manual/auto/mixta
    estado = db.Column(db.String(20), default="borrador", nullable=False)  # borrador/final

    total = db.Column(db.Numeric(6, 2), default=0, nullable=False)
    observaciones = db.Column(db.Text, nullable=True)