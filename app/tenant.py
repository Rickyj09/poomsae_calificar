from flask import g, session
from flask_login import current_user

def init_tenant(app):
    @app.before_request
    def resolve_tenant():
        """
        Regla:
        - Si usuario logueado -> tenant = current_user.academia_id
        - Si no -> tenant = session['academia_id'] (si fue seleccionada)
        """
        academia_id = None

        if getattr(current_user, "is_authenticated", False):
            academia_id = getattr(current_user, "academia_id", None)
        else:
            academia_id = session.get("academia_id")

        g.academia_id = academia_id