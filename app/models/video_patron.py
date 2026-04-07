from __future__ import annotations
from app.extensions import db
from app.models.mixins import TimestampMixin

class VideoPatron(TimestampMixin, db.Model):
    __tablename__ = "videos_patron"

    id = db.Column(db.Integer, primary_key=True)

    academia_id = db.Column(db.Integer, db.ForeignKey("academias.id"), nullable=False, index=True)
    poomsae_id  = db.Column(db.Integer, db.ForeignKey("poomsaes.id"), nullable=False, index=True)
    video_id    = db.Column(db.Integer, db.ForeignKey("videos.id"), nullable=False, index=True)

    # “activo” para historial, y asegurar solo 1 activo por academia+poomsae
    activo = db.Column(db.Boolean, default=True, nullable=False, index=True)

    __table_args__ = (
        db.UniqueConstraint("academia_id", "poomsae_id", "activo", name="uq_patron_acad_poom_activo"),
    )