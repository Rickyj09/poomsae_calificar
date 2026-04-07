from __future__ import annotations

import cv2
import numpy as np
from mediapipe import solutions as mp_solutions


mp_pose = mp_solutions.pose


def extract_pose_series(video_path: str, max_frames: int = 4000, sample_every: int = 1) -> dict:
    """
    Retorna una serie temporal simplificada:
    - fps
    - frames: lista con {t, hip_x, hip_y, shoulder_dist, visibility}
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    frames = []
    idx = 0

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose:

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            idx += 1
            if idx % sample_every != 0:
                continue

            # BGR->RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = pose.process(rgb)

            if not res.pose_landmarks:
                continue

            lm = res.pose_landmarks.landmark

            # indices mediapipe: L/R shoulder 11/12, L/R hip 23/24
            ls, rs = lm[11], lm[12]
            lh, rh = lm[23], lm[24]

            # Hip center (normalizado por imagen 0..1)
            hip_x = (lh.x + rh.x) / 2.0
            hip_y = (lh.y + rh.y) / 2.0

            # Shoulder dist (normalizado 0..1) para escalar
            shoulder_dist = float(np.sqrt((ls.x - rs.x) ** 2 + (ls.y - rs.y) ** 2))

            visibility = float(min(ls.visibility, rs.visibility, lh.visibility, rh.visibility))

            t = float(idx / fps)

            frames.append({
                "t": float(t),
                "hip_x": float(hip_x),
                "hip_y": float(hip_y),
                "shoulder_dist": float(shoulder_dist),
                "visibility": visibility,
            })

            if len(frames) >= max_frames:
                break

    cap.release()

    if len(frames) < 10:
        raise RuntimeError("No se detectó pose suficiente (muy pocos frames).")

    return {"fps": float(fps), "frames": frames}