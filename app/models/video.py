from __future__ import annotations

from app.extensions import db
from app.models.mixins import TimestampMixin


class Video(TimestampMixin, db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)

    academia_id = db.Column(db.Integer, db.ForeignKey("academias.id"), nullable=False, index=True)
    alumno_id = db.Column(db.Integer, db.ForeignKey("alumnos.id"), nullable=False, index=True)

    # ✅ a qué poomsae pertenece este video
    poomsae_id = db.Column(db.Integer, db.ForeignKey("poomsaes.id"), nullable=True, index=True)

    filename = db.Column(db.String(255), nullable=False)
    rel_path = db.Column(db.String(500), nullable=False)
    mime_type = db.Column(db.String(80), nullable=True)
    size_bytes = db.Column(db.Integer, nullable=True)

    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships opcionales
    poomsae = db.relationship("Poomsae", lazy="joined")
    alumno = db.relationship("Alumno", lazy="joined")