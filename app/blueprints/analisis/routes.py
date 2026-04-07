from __future__ import annotations

import os
import threading
from datetime import datetime
from decimal import Decimal

from flask import render_template, redirect, url_for, flash, g, current_app
from flask_login import login_required

from app.blueprints.analisis import analisis_bp
from app.extensions import db
from app.models.video import Video
from app.models.analisis_video import AnalisisVideo
from app.models.video_patron import VideoPatron

from app.services.pose_extractor import extract_pose_series
from app.services.checklist_scoring import score_checklist_sprint1

# Sprint 2
from app.services.pattern_alignment import align_and_score
from app.services.segment_checklist import checklist_from_segments


def _abs_video_path(video: Video) -> str:
    return os.path.join(current_app.static_folder, video.rel_path.replace("/", os.sep))

def _run_analysis(app, analisis_id: int, video_id: int):
    with app.app_context():
        an = db.session.get(AnalisisVideo, analisis_id)
        video = db.session.get(Video, video_id)
        if not an or not video:
            return

        try:
            # =========================
            # Sprint 1
            # =========================
            video_abs = _abs_video_path(video)
            pose = extract_pose_series(video_abs, max_frames=2500, sample_every=2)
            s1 = score_checklist_sprint1(pose)

            metrics_all = {
                "sprint1": s1.get("metrics") or {},
            }
            warnings_all = list(s1.get("warnings") or [])

            # Score base Sprint1
            similarity = float(al.get("similarity_score") or 0.0)

            segment_avg = 0.0
            if sprint2.get("segments"):
                segment_avg = sum(s["score"] for s in sprint2["segments"]) / len(sprint2["segments"])

            estabilidad = float(s1.get("score_estabilidad") or 0.0)
            ritmo = float(s1.get("score_ritmo") or 0.0)

            score_total = (
                0.35 * similarity +
                0.25 * segment_avg +
                0.25 * estabilidad +
                0.15 * ritmo
            )

            # =========================
            # Sprint 2 (Comparación contra patrón)
            # =========================
            sprint2 = {
                "enabled": False,
                "reason": None,
                "patron_video_id": None,
                "alignment": None,
                "segments": [],
                "segment_checklist": None,
            }

            if not video.poomsae_id:
                sprint2["reason"] = "El video no tiene poomsae_id (no se puede buscar patrón)."
            else:
                pat = (
                    VideoPatron.query
                    .filter_by(
                        academia_id=video.academia_id,
                        poomsae_id=video.poomsae_id,
                        activo=True
                    )
                    .first()
                )

                if not pat:
                    sprint2["reason"] = "No existe video patrón activo para esta poomsae."
                else:
                    sprint2["patron_video_id"] = pat.video_id

                    patron_video = db.session.get(Video, pat.video_id)
                    if not patron_video or not patron_video.activo:
                        sprint2["reason"] = "El patrón apunta a un video inexistente o inactivo."
                    else:
                        patron_abs = _abs_video_path(patron_video)

                        # Extraer pose del patrón
                        pose_pat = extract_pose_series(patron_abs, max_frames=2500, sample_every=2)

                        # ✅ Alignment: alumno vs patrón (orden correcto)
                        # Alignment (DTW)
                        al = align_and_score(pose, pose_pat)  # alumno, patrón (tu align_and_score ya está así)

                        # ✅ Aplanar claves importantes para que el template las lea directo
                        for k in ("dtw_dist", "dtw_good", "dtw_bad", "similarity_score", "path_len", "len_a", "len_b"):
                            sprint2[k] = al.get(k)

                        sprint2["segments"] = al.get("segments") or []

                        # Esperamos que align_and_score retorne:
                        # dtw_dist, similarity_score, path_len, segments (+ opcional len_a,len_b)
                        sprint2["enabled"] = True
                        sprint2["alignment"] = {k: al.get(k) for k in al.keys() if k != "segments"}
                        sprint2["segments"] = al.get("segments") or []

                        if sprint2["segments"]:
                            sprint2["segment_checklist"] = checklist_from_segments(sprint2["segments"])
                        else:
                            sprint2["reason"] = "Alignment no generó segmentos (revisar pose/DTW o llaves)."

                        # ✅ Score Sprint2: usa similarity_score (0-100)
                        s2_score = float(al.get("similarity_score") or 0.0)

                        # ✅ Mezcla de score (ajusta pesos a tu criterio)
                        # ejemplo: 70% sprint1 + 30% sprint2
                        score_total = 0.70 * score_total + 0.30 * s2_score

            metrics_all["sprint2"] = sprint2

            # =========================
            # Persistencia
            # =========================
            an.score_total = Decimal(str(round(score_total, 2)))
            an.score_estabilidad = Decimal(str(s1.get("score_estabilidad") or 0))
            an.score_ritmo = Decimal(str(s1.get("score_ritmo") or 0))

            an.metrics_json = metrics_all
            an.warnings_json = warnings_all

            an.estado = "listo"
            an.error_msg = None
            if hasattr(an, "finished_at"):
                an.finished_at = datetime.utcnow()

            db.session.commit()

        except Exception as e:
            an.estado = "error"
            an.error_msg = str(e)[:255]
            db.session.commit()



@analisis_bp.route("/videos/<int:video_id>/analizar", methods=["POST"])
@login_required
def analizar(video_id: int):
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    video = Video.query.filter_by(
        id=video_id, academia_id=g.academia_id, activo=True
    ).first_or_404()

    an = AnalisisVideo.query.filter_by(
        academia_id=g.academia_id, video_id=video.id, activo=True
    ).first()

    if not an:
        an = AnalisisVideo(academia_id=g.academia_id, video_id=video.id, estado="pendiente")
        db.session.add(an)
        db.session.commit()

    if an.estado == "en_proceso":
        flash("Este video ya se está analizando. Recarga en unos segundos.", "info")
        return redirect(url_for("analisis.ver", video_id=video.id))

    # Validar que exista archivo
    video_abs = os.path.join(current_app.static_folder, video.rel_path.replace("/", os.sep))
    if not os.path.exists(video_abs):
        flash("No se encontró el archivo del video en disco.", "danger")
        return redirect(url_for("videos.index"))

    an.estado = "en_proceso"
    an.error_msg = None
    if hasattr(an, "started_at"):
        an.started_at = datetime.utcnow()
    db.session.commit()

    app = current_app._get_current_object()
    t = threading.Thread(target=_run_analysis, args=(app, an.id, video.id), daemon=True)
    t.start()

    flash("Análisis IA iniciado (Sprint 1 + Sprint 2 si hay patrón).", "info")
    return redirect(url_for("analisis.ver", video_id=video.id))


@analisis_bp.route("/videos/<int:video_id>/analisis")
@login_required
def ver(video_id: int):
    if not g.academia_id:
        flash("No hay academia seleccionada.", "warning")
        return redirect(url_for("public.home"))

    video = Video.query.filter_by(
        id=video_id, academia_id=g.academia_id, activo=True
    ).first_or_404()

    an = AnalisisVideo.query.filter_by(
        academia_id=g.academia_id, video_id=video.id, activo=True
    ).first()

    return render_template("analisis/ver.html", video=video, analisis=an)