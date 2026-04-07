from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from flask_login import login_required

from app.extensions import db
from app.models.alumno import Alumno

alumnos_bp = Blueprint("alumnos", __name__)

@alumnos_bp.route("/alumnos")
@login_required
def index():
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    alumnos = (
        Alumno.query
        .filter_by(academia_id=g.academia_id, activo=True)
        .order_by(Alumno.apellidos.asc(), Alumno.nombres.asc())
        .all()
    )
    return render_template("alumnos/index.html", alumnos=alumnos)

@alumnos_bp.route("/alumnos/nuevo", methods=["GET", "POST"])
@login_required
def nuevo():
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    if request.method == "POST":
        nombres = (request.form.get("nombres") or "").strip()
        apellidos = (request.form.get("apellidos") or "").strip()
        documento = (request.form.get("documento") or "").strip() or None
        cinturon = (request.form.get("cinturon") or "").strip() or None

        if not nombres or not apellidos:
            flash("Nombres y apellidos son obligatorios.", "danger")
            return render_template("alumnos/form.html", alumno=None)

        alumno = Alumno(
            academia_id=g.academia_id,
            nombres=nombres,
            apellidos=apellidos,
            documento=documento,
            cinturon=cinturon,
            activo=True,
        )
        db.session.add(alumno)
        db.session.commit()

        flash("Alumno creado.", "success")
        return redirect(url_for("alumnos.index"))

    return render_template("alumnos/form.html", alumno=None)

@alumnos_bp.route("/alumnos/<int:alumno_id>/editar", methods=["GET", "POST"])
@login_required
def editar(alumno_id: int):
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    alumno = Alumno.query.filter_by(id=alumno_id, academia_id=g.academia_id).first_or_404()

    if request.method == "POST":
        alumno.nombres = (request.form.get("nombres") or "").strip()
        alumno.apellidos = (request.form.get("apellidos") or "").strip()
        alumno.documento = (request.form.get("documento") or "").strip() or None
        alumno.cinturon = (request.form.get("cinturon") or "").strip() or None

        if not alumno.nombres or not alumno.apellidos:
            flash("Nombres y apellidos son obligatorios.", "danger")
            return render_template("alumnos/form.html", alumno=alumno)

        db.session.commit()
        flash("Alumno actualizado.", "success")
        return redirect(url_for("alumnos.index"))

    return render_template("alumnos/form.html", alumno=alumno)

@alumnos_bp.route("/alumnos/<int:alumno_id>/eliminar", methods=["POST"])
@login_required
def eliminar(alumno_id: int):
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    alumno = Alumno.query.filter_by(id=alumno_id, academia_id=g.academia_id).first_or_404()
    alumno.activo = False
    db.session.commit()

    flash("Alumno eliminado (inactivo).", "info")
    return redirect(url_for("alumnos.index"))