from datetime import datetime
from app.extensions import db

class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class TenantMixin:
    academia_id = db.Column(db.Integer, nullable=False, index=True)