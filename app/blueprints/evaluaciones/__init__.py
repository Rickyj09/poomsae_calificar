from flask import Blueprint

evaluaciones_bp = Blueprint("evaluaciones", __name__)

from . import routes  # noqa