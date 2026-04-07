# app/services/segment_checklist.py
from __future__ import annotations


def checklist_from_segments(segment_scores: list[dict]) -> tuple[float, list[dict], dict]:
    """
    Convierte segmentos DTW en:
    - score_segmentos (0-100): promedio simple de scores por segmento
    - warnings: top segmentos peores (si score bajo)
    - metrics: extras para UI/debug

    Es tolerante: soporta llaves canónicas (segment, mean_dist)
    o legacy (k, dtw_dist).
    """
    if not segment_scores:
        return (
            0.0,
            [{"tipo": "patron", "detalle": "No se pudo alinear contra el patrón.", "sev": "alta"}],
            {},
        )

    # Scores seguros
    scores = [float(s.get("score") or 0.0) for s in segment_scores]
    avg = sum(scores) / max(len(scores), 1)

    # Top 2 peores
    worst = sorted(segment_scores, key=lambda x: float(x.get("score") or 0.0))[:2]

    warnings: list[dict] = []
    for w in worst:
        sc = float(w.get("score") or 0.0)
        seg_id = w.get("segment", w.get("k", "?"))
        dist = w.get("mean_dist", w.get("dtw_dist", None))

        if sc < 50:
            warnings.append(
                {
                    "tipo": "segmento",
                    "detalle": f"Desviación alta vs patrón en segmento {seg_id} (score {round(sc,2)}, dist {dist}).",
                    "sev": "media" if sc >= 35 else "alta",
                }
            )

    metrics = {
        "segment_avg_score": round(float(avg), 2),
        "segments": segment_scores,
        "worst_segments": [
            {"segment": w.get("segment", w.get("k", "?")), "score": w.get("score"), "mean_dist": w.get("mean_dist", w.get("dtw_dist"))}
            for w in worst
        ],
    }

    return round(float(avg), 2), warnings, metrics