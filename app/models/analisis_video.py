from __future__ import annotations

from app.extensions import db
from app.models.mixins import TimestampMixin


class AnalisisVideo(TimestampMixin, db.Model):
    __tablename__ = "analisis_videos"

    id = db.Column(db.Integer, primary_key=True)

    academia_id = db.Column(db.Integer, db.ForeignKey("academias.id"), nullable=False, index=True)
    video_id = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False, index=True)

    estado = db.Column(db.String(20), default="pendiente", nullable=False, index=True)
    # pendiente | en_proceso | listo | error

    score_total = db.Column(db.Numeric(6, 2), nullable=True)
    score_estabilidad = db.Column(db.Numeric(6, 2), nullable=True)
    score_ritmo = db.Column(db.Numeric(6, 2), nullable=True)

    warnings_json = db.Column(db.JSON, nullable=True)
    metrics_json = db.Column(db.JSON, nullable=True)

    error_msg = db.Column(db.String(255), nullable=True)

    activo = db.Column(db.Boolean, default=True, nullable=False)