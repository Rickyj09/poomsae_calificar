# app/services/pattern_alignment.py
from __future__ import annotations

import numpy as np


def _to_xy_series(pose: dict) -> np.ndarray:
    """
    Serie Nx2 normalizada (hip_x/shoulder_dist, hip_y/shoulder_dist).
    Basada en el centro de cadera para tener una señal estable.
    """
    frames = pose.get("frames") or []
    if not frames:
        return np.zeros((0, 2), dtype=np.float32)

    xs = np.array([f.get("hip_x", 0.0) for f in frames], dtype=np.float32)
    ys = np.array([f.get("hip_y", 0.0) for f in frames], dtype=np.float32)
    sds = np.array([max(float(f.get("shoulder_dist", 1e-6)), 1e-6) for f in frames], dtype=np.float32)

    nx = nx - np.mean(nx)
    ny = ny - np.mean(ny)
    return np.stack([nx, ny], axis=1)  # (N,2)


def _dtw_path(A: np.ndarray, B: np.ndarray, band_ratio: float = 0.12) -> tuple[float, list[tuple[int, int]]]:
    """
    DTW con banda Sakoe-Chiba simple.
    Retorna (distancia_total_normalizada, path)

    - A: (N,D)
    - B: (M,D)
    """
    n, m = int(len(A)), int(len(B))
    if n < 5 or m < 5:
        return 1e9, []

    w = int(max(n, m) * float(band_ratio))
    w = max(w, abs(n - m))

    INF = 1e18
    D = np.full((n + 1, m + 1), INF, dtype=np.float64)
    D[0, 0] = 0.0

    def cost(i: int, j: int) -> float:
        d = A[i] - B[j]
        # euclídea en 2D
        return float(np.sqrt(d[0] * d[0] + d[1] * d[1]))

    for i in range(1, n + 1):
        j_start = max(1, i - w)
        j_end = min(m, i + w)
        for j in range(j_start, j_end + 1):
            c = cost(i - 1, j - 1)
            D[i, j] = c + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])

    # backtrack path
    i, j = n, m
    if not np.isfinite(D[i, j]):
        return 1e9, []

    path: list[tuple[int, int]] = []
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        choices = [
            (D[i - 1, j], i - 1, j),
            (D[i, j - 1], i, j - 1),
            (D[i - 1, j - 1], i - 1, j - 1),
        ]
        _, i, j = min(choices, key=lambda x: x[0])

    path.reverse()

    dist = float(D[n, m]) / max(len(path), 1)
    return dist, path


def _segment_scores_from_path(
    A: np.ndarray,
    B: np.ndarray,
    path: list[tuple[int, int]],
    segments: int = 6,
    good: float = 0.02,
    bad: float = 0.10,
) -> list[dict]:
    """
    Segmenta sobre el eje del patrón (B) en 'segments' tramos.
    Devuelve una lista de dicts con llaves ESTABLES para UI y checklist:

    - segment (1..segments)
    - score (0..100)
    - mean_dist (float o None)
    - frames_a, frames_b
    - len_a, len_b
    - a_range [a0,a1] o None
    - b_range [b0,b1] o None
    - a_start, a_end, b_start, b_end (redundante pero útil para UI)
    - info
    """
    N = int(len(A))
    M = int(len(B))

    if N == 0 or M == 0 or not path:
        return [
            {
                "segment": k + 1,
                "score": 0.0,
                "mean_dist": None,
                "frames_a": 0,
                "frames_b": 0,
                "len_a": N,
                "len_b": M,
                "a_range": None,
                "b_range": None,
                "a_start": None,
                "a_end": None,
                "b_start": None,
                "b_end": None,
                "info": "sin datos (A/B vacíos o path vacío)",
            }
            for k in range(segments)
        ]

    edges = np.linspace(0, M, segments + 1).astype(int)

    out: list[dict] = []
    for k in range(segments):
        j0, j1 = int(edges[k]), int(edges[k + 1])

        # último segmento incluye el borde final
        if k == segments - 1:
            pairs = [(i, j) for (i, j) in path if (j >= j0 and j <= j1 - 1)]
        else:
            pairs = [(i, j) for (i, j) in path if (j >= j0 and j < j1)]

        if not pairs:
            out.append(
                {
                    "segment": k + 1,
                    "score": 0.0,
                    "mean_dist": None,
                    "frames_a": 0,
                    "frames_b": (j1 - j0),
                    "len_a": N,
                    "len_b": M,
                    "a_range": None,
                    "b_range": [j0, j1],
                    "a_start": None,
                    "a_end": None,
                    "b_start": j0,
                    "b_end": j1,
                    "info": f"sin pares DTW en tramo B[{j0}:{j1}]",
                }
            )
            continue

        a_idx = np.array([p[0] for p in pairs], dtype=int)
        b_idx = np.array([p[1] for p in pairs], dtype=int)

        d = A[a_idx] - B[b_idx]
        dist_seg = float(np.mean(np.sqrt(np.sum(d * d, axis=1))))

        # map dist -> score
        x = (dist_seg - good) / (bad - good)
        x = float(max(0.0, min(1.0, x)))
        score_seg = (1.0 - x) * 100.0

        a0, a1 = int(a_idx.min()), int(a_idx.max())
        b0, b1 = int(b_idx.min()), int(b_idx.max())

        out.append(
            {
                "segment": k + 1,
                "score": round(float(score_seg), 2),
                "mean_dist": round(float(dist_seg), 6),
                "frames_a": int(a1 - a0 + 1),
                "frames_b": int(b1 - b0 + 1),
                "len_a": N,
                "len_b": M,
                "a_range": [a0, a1],
                "b_range": [b0, b1],
                "a_start": a0,
                "a_end": a1,
                "b_start": b0,
                "b_end": b1,
                "info": f"B[{j0}:{j1}] pares={len(pairs)}",
            }
        )

    return out


def align_and_score(pose_student: dict, pose_pattern: dict) -> dict:
    """
    Alinea (DTW) alumno vs patrón y devuelve métricas para Sprint2.

    Retorna:
    - dtw_dist (mientras menor mejor)
    - similarity_score (0-100)
    - path_len
    - segments: lista por segmento (6 tramos) con llaves canónicas:
        segment, score, mean_dist, a_range/b_range, etc.
    - len_a, len_b
    """
    A = _to_xy_series(pose_student)   # alumno
    B = _to_xy_series(pose_pattern)   # patrón

    dist, path = _dtw_path(A, B, band_ratio=0.12)

    # dist <= 0.02 muy parecido; dist >= 0.10 muy diferente
    good, bad = 0.5, 3.00
    x = (dist - good) / (bad - good)
    x = float(max(0.0, min(1.0, x)))
    similarity = (1.0 - x) * 100.0

    segments = _segment_scores_from_path(A, B, path, segments=6, good=good, bad=bad)

    return {
        "dtw_dist": round(float(dist), 6),
        "dtw_good": good,
        "dtw_bad": bad,
        "similarity_score": round(float(similarity), 2),
        "path_len": int(len(path)),
        "segments": segments,        # ✅ clave canónica para UI
        "len_a": int(len(A)),
        "len_b": int(len(B)),
    }