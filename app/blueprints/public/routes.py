from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from app.extensions import db
from app.models.academia import Academia
from app.models.user import User

public_bp = Blueprint("public", __name__)

@public_bp.route("/")
def home():
    academias = Academia.query.filter_by(activo=True).order_by(Academia.nombre.asc()).all()
    return render_template("public/select_academia.html", academias=academias)

@public_bp.route("/select-academia", methods=["POST"])
def select_academia():
    academia_id = request.form.get("academia_id", type=int)
    if not academia_id:
        flash("Selecciona una academia.", "danger")
        return redirect(url_for("public.home"))

    aca = Academia.query.get(academia_id)
    if not aca or not aca.activo:
        flash("Academia inválida.", "danger")
        return redirect(url_for("public.home"))

    session["academia_id"] = aca.id
    flash(f"Academia seleccionada: {aca.nombre}", "success")
    return redirect(url_for("auth.login"))

@public_bp.route("/seed", methods=["GET"])
def seed():
    """
    SOLO DEV: crea 1 academia + 1 admin.
    URL: /seed
    Credenciales:
      admin@demo.com / Admin123!
    """
    if Academia.query.filter_by(slug="demo").first():
        flash("Seed ya fue ejecutado.", "info")
        return redirect(url_for("public.home"))

    aca = Academia(nombre="Academia Demo", slug="demo", activo=True)
    db.session.add(aca)
    db.session.flush()

    admin = User(academia_id=aca.id, email="admin@demo.com", rol="admin", activo=True)
    admin.set_password("Admin123!")
    db.session.add(admin)

    db.session.commit()
    flash("Seed OK: Academia Demo + admin creado.", "success")
    return redirect(url_for("public.home"))

@public_bp.route("/debug-static")
def debug_static():
    return {
        "static_folder": current_app.static_folder,
        "upload_folder_config": current_app.config.get("UPLOAD_FOLDER"),
    }