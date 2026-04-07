from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from flask import g

from app.models.user import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        # Si NO hay tenant seleccionado, no dejamos loguear
        if not g.academia_id:
            flash("Primero selecciona una academia.", "warning")
            return redirect(url_for("public.home"))

        user = User.query.filter_by(academia_id=g.academia_id, email=email, activo=True).first()

        if not user or not user.check_password(password):
            flash("Credenciales inválidas.", "danger")
            return render_template("auth/login.html")

        login_user(user, remember=True)
        flash("Login OK.", "success")
        return redirect(url_for("public.home"))

    return render_template("auth/login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("public.home"))