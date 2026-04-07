from __future__ import annotations

import numpy as np
from typing import Any


W_STAB = 0.55
W_RHY = 0.45


def _clip01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def _moving_average(x: np.ndarray, k: int = 5) -> np.ndarray:
    if x.size < k:
        return x
    kernel = np.ones(k, dtype=np.float32) / float(k)
    return np.convolve(x, kernel, mode="same")


def score_stability(pose: dict) -> tuple[float, dict, list]:
    """
    Estabilidad = control del centro (hip center) medido por desplazamiento frame-to-frame (drift).
    Separar:
      - drift típico (percentiles) -> estabilidad del ejecutante
      - jitter alto -> posible cámara movida / tracking ruidoso
    """
    frames = pose["frames"]
    xs = np.array([f["hip_x"] for f in frames], dtype=np.float32)
    ys = np.array([f["hip_y"] for f in frames], dtype=np.float32)
    sds = np.array([max(f["shoulder_dist"], 1e-6) for f in frames], dtype=np.float32)

    if xs.size < 10:
        return 0.0, {"error": "muy pocos datos"}, [{
            "tipo": "estabilidad",
            "detalle": "Video muy corto o poca detección de pose para medir estabilidad.",
            "sev": "alta",
        }]

    # Drift frame-to-frame normalizado por tamaño corporal
    dx = np.diff(xs) / sds[1:]
    dy = np.diff(ys) / sds[1:]
    dr = np.sqrt(dx * dx + dy * dy)

    # Suavizado para reducir ruido
    k = 5
    dr_s = _moving_average(dr, k=k)

    drift_mean = float(np.mean(dr_s))
    drift_std = float(np.std(dr_s))
    drift_p50 = float(np.percentile(dr_s, 50))
    drift_p95 = float(np.percentile(dr_s, 95))

    # Indicador de "jitter" (cámara/ruido): std relativo respecto a mediana
    jitter_ratio = float(drift_std / (drift_p50 + 1e-6))

    # Métrica principal: que sea robusta (p95 captura picos de inestabilidad)
    stability_metric = float(0.65 * drift_p95 + 0.35 * drift_mean)

    # ✅ Umbrales iniciales más realistas (calibrables)
    # - good: cámara estable + ejecución estable
    # - bad: mucha oscilación / cámara movida
    good, bad = 0.03, 0.12

    x = (stability_metric - good) / (bad - good)
    score = (1.0 - _clip01(x)) * 100.0

    warnings = []

    # Heurística: jitter_ratio alto sugiere cámara movida o tracking inestable
    if jitter_ratio > 2.5:
        warnings.append({
            "tipo": "estabilidad",
            "detalle": "Se detecta mucho 'jitter' (posible cámara movida o tracking ruidoso). Usa trípode y plano completo.",
            "sev": "alta",
        })

    if stability_metric >= bad:
        warnings.append({
            "tipo": "estabilidad",
            "detalle": "Mucha oscilación del centro (posible pérdida de balance o desplazamiento excesivo).",
            "sev": "alta",
        })
    elif stability_metric >= (good + 0.6 * (bad - good)):
        warnings.append({
            "tipo": "estabilidad",
            "detalle": "Oscilación moderada del centro. Revisa control del tronco y apoyos.",
            "sev": "media",
        })

    metrics = {
        "stability_metric": round(stability_metric, 6),
        "drift_mean": round(drift_mean, 6),
        "drift_std": round(drift_std, 6),
        "drift_p50": round(drift_p50, 6),
        "drift_p95": round(drift_p95, 6),
        "jitter_ratio": round(jitter_ratio, 6),
        "smooth_k": k,
        "threshold_good": good,
        "threshold_bad": bad,
    }
    return round(score, 2), metrics, warnings


def score_rhythm(pose: dict) -> tuple[float, dict, list]:
    """
    Ritmo = consistencia de velocidad + proporción de pausas razonable.
    Usamos velocidad del centro de cadera (normalizado por hombros).
    """
    frames = pose["frames"]
    ts = np.array([f["t"] for f in frames], dtype=np.float32)
    xs = np.array([f["hip_x"] for f in frames], dtype=np.float32)
    ys = np.array([f["hip_y"] for f in frames], dtype=np.float32)
    sds = np.array([max(f["shoulder_dist"], 1e-6) for f in frames], dtype=np.float32)

    nx = xs / sds
    ny = ys / sds

    dt = np.diff(ts)
    dx = np.diff(nx)
    dy = np.diff(ny)

    dt[dt <= 1e-6] = 1e-3

    v = np.sqrt(dx * dx + dy * dy) / dt  # velocidad normalizada

    if v.size < 10:
        return 0.0, {"error": "muy pocos datos"}, [{
            "tipo": "ritmo",
            "detalle": "Video muy corto o poca detección de pose para medir ritmo.",
            "sev": "alta",
        }]

    # Suavizado para evitar ruido frame-to-frame
    v_s = _moving_average(v, k=5)

    v_mean = float(np.mean(v_s))
    v_std = float(np.std(v_s))

    if v_mean < 1e-6:
        cv = 10.0
    else:
        cv = float(v_std / v_mean)

    pause_thr = max(0.15 * v_mean, 0.02)
    pause_ratio = float(np.mean(v_s < pause_thr))

    cv_good_low, cv_good_high = 0.5, 1.2
    pr_good_low, pr_good_high = 0.15, 0.35

    cv_pen = 0.0
    if cv < cv_good_low:
        cv_pen = (cv_good_low - cv) / cv_good_low
    elif cv > cv_good_high:
        cv_pen = (cv - cv_good_high) / cv_good_high
    cv_score = (1.0 - _clip01(cv_pen)) * 100.0

    pr_pen = 0.0
    if pause_ratio < pr_good_low:
        pr_pen = (pr_good_low - pause_ratio) / pr_good_low
    elif pause_ratio > pr_good_high:
        pr_pen = (pause_ratio - pr_good_high) / pr_good_high
    pr_score = (1.0 - _clip01(pr_pen)) * 100.0

    score = 0.6 * cv_score + 0.4 * pr_score

    warnings = []
    if pause_ratio > 0.45:
        warnings.append({"tipo": "ritmo", "detalle": "Exceso de pausas (ritmo muy cortado).", "sev": "media"})
    if pause_ratio < 0.08:
        warnings.append({"tipo": "ritmo", "detalle": "Casi sin pausas (posible ejecución apresurada).", "sev": "media"})
    if cv > 1.6:
        warnings.append({"tipo": "ritmo", "detalle": "Ritmo errático (cambios bruscos de velocidad).", "sev": "media"})

    metrics = {
        "v_mean": round(v_mean, 5),
        "v_std": round(v_std, 5),
        "cv": round(cv, 5),
        "pause_thr": round(float(pause_thr), 5),
        "pause_ratio": round(pause_ratio, 5),
        "smooth_k": 5,
    }
    return round(score, 2), metrics, warnings


def score_checklist_sprint1(pose: dict) -> dict:
    s_stab, m_stab, w_stab = score_stability(pose)
    s_rhy, m_rhy, w_rhy = score_rhythm(pose)

    total = round(W_STAB * s_stab + W_RHY * s_rhy, 2)

    return {
        "score_total": total,
        "score_estabilidad": s_stab,
        "score_ritmo": s_rhy,
        "metrics": {"estabilidad": m_stab, "ritmo": m_rhy},
        "warnings": w_stab + w_rhy,
    }

def checklist_from_segments(segments: list[dict[str, Any]]) -> dict:
    """
    Construye checklist simple basado en segmentos DTW.
    Acepta segmentos con:
      - k (1..6)  o segment (1..6)
      - score
      - dtw_dist
      - a_range / b_range (opcional)
    """
    if not segments:
        return {"ok": False, "reason": "sin segmentos", "items": []}

    items = []
    for seg in segments:
        seg_id = seg.get("segment")
        if seg_id is None:
            seg_id = seg.get("k")  # <-- tu formato actual

        score = seg.get("score")
        dist = seg.get("dtw_dist")

        # Heurística simple: marcar “bien” si score >= 70
        estado = "ok" if (isinstance(score, (int, float)) and score >= 70.0) else "rev"

        items.append({
            "segment": seg_id,
            "estado": estado,
            "score": score,
            "dtw_dist": dist,
            "a_range": seg.get("a_range"),
            "b_range": seg.get("b_range"),
            "info": seg.get("info"),
        })

    # Resumen
    scores = [it["score"] for it in items if isinstance(it["score"], (int, float))]
    avg = round(sum(scores) / len(scores), 2) if scores else 0.0

    return {
        "ok": True,
        "segment_avg_score": avg,
        "items": items,
    }