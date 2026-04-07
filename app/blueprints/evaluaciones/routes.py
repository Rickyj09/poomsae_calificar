from __future__ import annotations

from decimal import Decimal

from flask import render_template, redirect, url_for, flash, request, g
from flask_login import login_required, current_user

from app.blueprints.evaluaciones import evaluaciones_bp
from app.extensions import db
from app.models.video import Video
from app.models.alumno import Alumno
from app.models.evaluacion import Evaluacion
from app.models.evaluacion_item import EvaluacionItem


CRITERIOS = [
    {"codigo": "accuracy", "nombre": "Precisión (Accuracy)", "max": Decimal("4.00")},
    {"codigo": "presentation", "nombre": "Presentación (Presentation)", "max": Decimal("6.00")},
]


def _to_decimal(value: str | None) -> Decimal:
    try:
        return Decimal(value or "0")
    except Exception:
        return Decimal("0")


@evaluaciones_bp.route("/evaluaciones")
@login_required
def index():
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    evaluaciones = (
        Evaluacion.query
        .filter_by(academia_id=g.academia_id, activo=True)
        .order_by(Evaluacion.created_at.desc())
        .all()
    )
    return render_template("evaluaciones/index.html", evaluaciones=evaluaciones)


@evaluaciones_bp.route("/evaluaciones/crear/<int:video_id>")
@login_required
def crear_desde_video(video_id: int):
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    video = Video.query.filter_by(id=video_id, academia_id=g.academia_id, activo=True).first_or_404()

    # Si ya hay evaluación borrador para este video y juez (opcional), reusar:
    ev = (
        Evaluacion.query
        .filter_by(academia_id=g.academia_id, video_id=video.id, activo=True, estado="borrador")
        .order_by(Evaluacion.created_at.desc())
        .first()
    )
    if not ev:
        ev = Evaluacion(
            academia_id=g.academia_id,
            video_id=video.id,
            juez_user_id=getattr(current_user, "id", None),
            tipo="manual",
            estado="borrador",
            total=Decimal("0.00"),
        )
        db.session.add(ev)
        db.session.flush()  # para tener ev.id

        for c in CRITERIOS:
            item = EvaluacionItem(
                evaluacion_id=ev.id,
                criterio_codigo=c["codigo"],
                criterio_nombre=c["nombre"],
                puntaje=Decimal("0.00"),
                max_puntaje=c["max"],
            )
            db.session.add(item)

        db.session.commit()

    return redirect(url_for("evaluaciones.editar", evaluacion_id=ev.id))


@evaluaciones_bp.route("/evaluaciones/<int:evaluacion_id>", methods=["GET"])
@login_required
def editar(evaluacion_id: int):
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    ev = Evaluacion.query.filter_by(id=evaluacion_id, academia_id=g.academia_id, activo=True).first_or_404()
    video = Video.query.filter_by(id=ev.video_id, academia_id=g.academia_id, activo=True).first_or_404()
    alumno = Alumno.query.filter_by(id=video.alumno_id, academia_id=g.academia_id, activo=True).first()

    items = (
        EvaluacionItem.query
        .filter_by(evaluacion_id=ev.id, activo=True)
        .order_by(EvaluacionItem.id.asc())
        .all()
    )

    return render_template(
        "evaluaciones/editar.html",
        ev=ev,
        video=video,
        alumno=alumno,
        items=items
    )


@evaluaciones_bp.route("/evaluaciones/<int:evaluacion_id>/guardar", methods=["POST"])
@login_required
def guardar(evaluacion_id: int):
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    ev = Evaluacion.query.filter_by(id=evaluacion_id, academia_id=g.academia_id, activo=True).first_or_404()

    items = EvaluacionItem.query.filter_by(evaluacion_id=ev.id, activo=True).all()

    total = Decimal("0.00")
    for item in items:
        field_name = f"puntaje_{item.id}"
        punt = _to_decimal(request.form.get(field_name))

        # clamp 0..max
        if punt < 0:
            punt = Decimal("0.00")
        if item.max_puntaje is not None and punt > Decimal(str(item.max_puntaje)):
            punt = Decimal(str(item.max_puntaje))

        item.puntaje = punt
        item.notas = (request.form.get(f"notas_{item.id}") or "").strip() or None
        total += punt

    ev.observaciones = (request.form.get("observaciones") or "").strip() or None
    accion = request.form.get("accion") or "borrador"
    ev.estado = "final" if accion == "final" else "borrador"
    ev.total = total

    db.session.commit()

    flash("Evaluación guardada.", "success")
    return redirect(url_for("evaluaciones.editar", evaluacion_id=ev.id))