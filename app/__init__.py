from flask import Flask
from dotenv import load_dotenv

from app.config import Development
from app.extensions import db, migrate, login_manager, csrf
from app.blueprints.alumnos.routes import alumnos_bp
from app.blueprints.videos.routes import videos_bp
from app.blueprints.evaluaciones import evaluaciones_bp
from app.blueprints.analisis import analisis_bp


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Development)

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"

    # Tenant resolver (g.academia_id)
    from app.tenant import init_tenant
    init_tenant(app)

    # Blueprints
    from app.blueprints.public.routes import public_bp
    from app.blueprints.auth.routes import auth_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(alumnos_bp)
    app.register_blueprint(videos_bp)
    app.register_blueprint(evaluaciones_bp)
    app.register_blueprint(analisis_bp)

    return app