import os
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.alumno import Alumno
from app.models.video import Video
from app.models.poomsae import Poomsae
from app.models.video_patron import VideoPatron
from app.utils.files import allowed_extension
from app.utils.strings import slugify

videos_bp = Blueprint("videos", __name__)


@videos_bp.route("/videos")
@login_required
def index():
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    videos = (
        Video.query
        .filter_by(academia_id=g.academia_id, activo=True)
        .order_by(Video.created_at.desc())
        .all()
    )

    alumnos = (
        Alumno.query
        .filter_by(academia_id=g.academia_id, activo=True)
        .all()
    )
    alumnos_map = {a.id: a for a in alumnos}

    # ✅ patron_map: { video_id: poomsae_code } para mostrar badges/botones
    patrones = (
        db.session.query(VideoPatron.video_id, Poomsae.codigo)
        .join(Poomsae, Poomsae.id == VideoPatron.poomsae_id)
        .filter(
            VideoPatron.academia_id == g.academia_id,
            VideoPatron.activo.is_(True),
        )
        .all()
    )
    patron_map = {vid: code for (vid, code) in patrones}

    return render_template(
        "videos/index.html",
        videos=videos,
        alumnos_map=alumnos_map,
        patron_map=patron_map,
    )

@videos_bp.route("/videos/nuevo", methods=["GET"])
@login_required
def nuevo():
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    alumnos = (
        Alumno.query
        .filter_by(academia_id=g.academia_id, activo=True)
        .order_by(Alumno.apellidos.asc(), Alumno.nombres.asc())
        .all()
    )

    poomsaes = (
        Poomsae.query
        .filter_by(activo=True)
        .order_by(Poomsae.nombre.asc())
        .all()
    )

    poomsaes = Poomsae.query.filter_by(activo=True).order_by(Poomsae.nombre.asc()).all()
    return render_template("videos/nuevo.html", alumnos=alumnos, poomsaes=poomsaes)


@videos_bp.route("/videos/subir", methods=["POST"])
@login_required
def subir():
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    alumno_id = request.form.get("alumno_id", type=int)
    if not alumno_id:
        flash("Selecciona un alumno.", "danger")
        return redirect(url_for("videos.nuevo"))

    alumno = Alumno.query.filter_by(
        id=alumno_id, academia_id=g.academia_id, activo=True
    ).first()
    if not alumno:
        flash("Alumno inválido.", "danger")
        return redirect(url_for("videos.nuevo"))
    poomsae_id = request.form.get("poomsae_id", type=int)
    if not poomsae_id:
        flash("Selecciona la poomsae.", "danger")
        return redirect(url_for("videos.nuevo"))

    poomsae = Poomsae.query.filter_by(id=poomsae_id, activo=True).first()
    if not poomsae:
        flash("Poomsae inválida.", "danger")
        return redirect(url_for("videos.nuevo"))

    file = request.files.get("video")
    if not file or not file.filename:
        flash("Selecciona un video para subir.", "danger")
        return redirect(url_for("videos.nuevo"))

    if not allowed_extension(file.filename, current_app.config["ALLOWED_VIDEO_EXTENSIONS"]):
        flash("Formato no permitido. Usa mp4/webm/mov/m4v.", "danger")
        return redirect(url_for("videos.nuevo"))

    base_upload = os.path.join(current_app.static_folder, "storage", "uploads")
    dest_dir = os.path.join(base_upload, str(g.academia_id), str(alumno_id))
    os.makedirs(dest_dir, exist_ok=True)

    original = secure_filename(file.filename)
    ext = os.path.splitext(original)[1].lower()

    base_name = slugify(f"{alumno.apellidos}_{alumno.nombres}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{base_name}_{timestamp}{ext}"
    abs_path = os.path.join(dest_dir, filename)

    counter = 2
    while os.path.exists(abs_path):
        filename = f"{base_name}_{timestamp}_{counter}{ext}"
        abs_path = os.path.join(dest_dir, filename)
        counter += 1

    file.save(abs_path)

    rel_path = f"storage/uploads/{g.academia_id}/{alumno_id}/{filename}"

    video = Video(
        academia_id=g.academia_id,
        alumno_id=alumno_id,
        poomsae_id=poomsae_id,
        filename=filename,
        rel_path=rel_path,
        mime_type=file.mimetype,
        size_bytes=os.path.getsize(abs_path),
        activo=True,
    )
    db.session.add(video)
    db.session.commit()

    flash("Video subido correctamente.", "success")
    return redirect(url_for("videos.index"))


@videos_bp.route("/videos/<int:video_id>/ver", methods=["GET"])
@login_required
def ver(video_id: int):
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    video = Video.query.filter_by(
        id=video_id, academia_id=g.academia_id, activo=True
    ).first_or_404()

    return redirect(url_for("static", filename=video.rel_path))


@videos_bp.route("/videos/<int:video_id>/eliminar", methods=["POST"], endpoint="eliminar")
@login_required
def eliminar(video_id: int):
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    video = Video.query.filter_by(
        id=video_id,
        academia_id=g.academia_id,
        activo=True
    ).first_or_404()

    # ✅ si este video era patrón activo, lo desactivamos
    VideoPatron.query.filter_by(
        academia_id=g.academia_id,
        video_id=video.id,
        activo=True
    ).update({"activo": False})

    # soft delete + borrar archivo físico
    video.activo = False

    abs_path = os.path.join(current_app.static_folder, video.rel_path.replace("/", os.sep))
    try:
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except Exception as e:
        print("ERROR deleting file:", e)

    db.session.commit()
    flash("Video eliminado.", "info")
    return redirect(url_for("videos.index"))

@videos_bp.route("/videos/<int:video_id>/set-patron", methods=["POST"])
@login_required
def set_patron(video_id: int):
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    video = Video.query.filter_by(
        id=video_id,
        academia_id=g.academia_id,
        activo=True
    ).first_or_404()

    if not video.poomsae_id:
        flash("Este video no tiene poomsae asignada. Súbelo nuevamente seleccionando poomsae.", "danger")
        return redirect(url_for("videos.index"))

    # Desactivar patrón anterior de esa poomsae en la academia
    VideoPatron.query.filter_by(
        academia_id=g.academia_id,
        poomsae_id=video.poomsae_id,
        activo=True
    ).update({"activo": False})

    patron = VideoPatron(
        academia_id=g.academia_id,
        poomsae_id=video.poomsae_id,
        video_id=video.id,
        activo=True
    )
    db.session.add(patron)
    db.session.commit()

    po = Poomsae.query.get(video.poomsae_id)
    flash(f"Video marcado como patrón: {po.nombre if po else 'Poomsae'}.", "success")
    return redirect(url_for("videos.index"))


    # Desactivar patrón anterior (si existe)
    VideoPatron.query.filter_by(
        academia_id=g.academia_id,
        poomsae_id=poomsae.id,
        activo=True
    ).update({"activo": False})

    patron = VideoPatron(
        academia_id=g.academia_id,
        poomsae_id=poomsae.id,
        video_id=video.id,
        activo=True
    )
    db.session.add(patron)
    db.session.commit()

    flash(f"Video marcado como patrón: {poomsae.nombre}.", "success")
    return redirect(url_for("videos.index"))