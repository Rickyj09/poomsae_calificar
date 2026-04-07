from flask import Blueprint

analisis_bp = Blueprint("analisis", __name__)

from . import routes  # noqa