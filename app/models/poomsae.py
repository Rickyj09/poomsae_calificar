from __future__ import annotations
from app.extensions import db

class Poomsae(db.Model):
    __tablename__ = "poomsaes"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False, index=True)   # ej: TAEGUK_1
    nombre = db.Column(db.String(120), nullable=False)                          # ej: Taeguk Il Jang
    activo = db.Column(db.Boolean, default=True, nullable=False)