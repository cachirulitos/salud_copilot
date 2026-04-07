"""
Professional video overlay for SaludCopilot CV Worker.

Draws area metadata, people count, status, ROI boundary, and tracking boxes
directly onto each frame so the demo window is self-explanatory.
"""

import time

import cv2
import numpy as np

from models.people_detector import (
    COLOR_OUTSIDE_ROI,
    DetectionFrame,
    status_color,
)

# Layout constants
TOP_BAR_H = 56
BOTTOM_BAR_H = 80
BAR_ALPHA = 0.72          # transparency of header/footer bars
ROI_FILL_ALPHA = 0.10     # fill opacity of ROI rectangle
PUBLISH_FLASH_SECONDS = 1.0  # how long the "ENVIANDO" indicator stays on

# Typography
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_BOLD = cv2.FONT_HERSHEY_DUPLEX

STATUS_LABELS = {
    "normal":    "NORMAL",
    "warning":   "ALERTA",
    "saturated": "SATURADO",
}


def _blend_rect(
    frame: np.ndarray,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: tuple[int, int, int],
    alpha: float,
) -> None:
    """Draw a semi-transparent filled rectangle on frame in-place."""
    roi_slice = frame[y1:y2, x1:x2]
    solid = np.full_like(roi_slice, color, dtype=np.uint8)
    cv2.addWeighted(solid, alpha, roi_slice, 1 - alpha, 0, roi_slice)


def draw_frame(
    frame: np.ndarray,
    detection: DetectionFrame,
    area_name: str,
    roi: tuple[int, int, int, int] | None,
    last_publish_time: float,
) -> np.ndarray:
    """Return a new annotated frame with overlay, tracking boxes, and ROI.

    Args:
        frame: Raw BGR frame from the capture source.
        detection: DetectionFrame with counts and track data.
        area_name: Human-readable area name shown in the top bar.
        roi: Optional (x1,y1,x2,y2) region rectangle to draw on the frame.
        last_publish_time: monotonic time of the last API publish, used to
            flash the "ENVIANDO" indicator.
    """
    out = frame.copy()
    h, w = out.shape[:2]
    color = detection.color

    # ── ROI rectangle ────────────────────────────────────────────────────
    if roi is not None:
        rx1, ry1, rx2, ry2 = roi
        _blend_rect(out, rx1, ry1, rx2, ry2, color, ROI_FILL_ALPHA)
        cv2.rectangle(out, (rx1, ry1), (rx2, ry2), color, 2)
        cv2.putText(
            out, "ZONA DE ESPERA",
            (rx1 + 6, ry1 + 20),
            FONT, 0.5, color, 1, cv2.LINE_AA,
        )

    # ── Tracking boxes ───────────────────────────────────────────────────
    for x1, y1, x2, y2, tid in detection.tracks_outside_roi:
        cv2.rectangle(out, (x1, y1), (x2, y2), COLOR_OUTSIDE_ROI, 1)

    for x1, y1, x2, y2, tid in detection.tracks_in_roi:
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        label = f"#{tid}" if tid >= 0 else ""
        if label:
            cv2.putText(
                out, label,
                (x1 + 4, y1 - 6),
                FONT, 0.45, color, 1, cv2.LINE_AA,
            )

    # ── Top bar ──────────────────────────────────────────────────────────
    _blend_rect(out, 0, 0, w, TOP_BAR_H, (10, 10, 10), BAR_ALPHA)

    cv2.putText(
        out, "SaludCopilot  CV",
        (12, 22), FONT, 0.55, (180, 180, 180), 1, cv2.LINE_AA,
    )
    cv2.putText(
        out, area_name.upper(),
        (12, 44), FONT_BOLD, 0.75, (255, 255, 255), 1, cv2.LINE_AA,
    )

    # Publishing flash indicator (top-right)
    elapsed = time.monotonic() - last_publish_time
    if elapsed < PUBLISH_FLASH_SECONDS:
        dot_color = (80, 220, 80)
        label = "ENVIANDO"
    else:
        dot_color = (80, 80, 80)
        label = "EN VIVO"

    cv2.circle(out, (w - 14, 18), 6, dot_color, -1, cv2.LINE_AA)
    cv2.putText(
        out, label,
        (w - 85, 23), FONT, 0.45, dot_color, 1, cv2.LINE_AA,
    )

    # ── Bottom bar ───────────────────────────────────────────────────────
    _blend_rect(out, 0, h - BOTTOM_BAR_H, w, h, (10, 10, 10), BAR_ALPHA)

    # Large count number
    count_str = str(detection.count)
    cv2.putText(
        out, count_str,
        (18, h - 16), FONT_BOLD, 2.0, color, 3, cv2.LINE_AA,
    )

    # Label next to count
    digit_w = 38 * len(count_str)
    cv2.putText(
        out, "personas en espera",
        (18 + digit_w + 8, h - 32), FONT, 0.52, (200, 200, 200), 1, cv2.LINE_AA,
    )
    cv2.putText(
        out, "dentro de la zona",
        (18 + digit_w + 8, h - 12), FONT, 0.45, (140, 140, 140), 1, cv2.LINE_AA,
    )

    # Status pill (right side)
    status_label = STATUS_LABELS.get(detection.status, detection.status.upper())
    pill_x = w - 130
    pill_y = h - BOTTOM_BAR_H + 14
    cv2.rectangle(out, (pill_x, pill_y), (w - 10, pill_y + 30), color, -1, cv2.LINE_AA)
    cv2.putText(
        out, status_label,
        (pill_x + 8, pill_y + 22), FONT_BOLD, 0.6, (10, 10, 10), 1, cv2.LINE_AA,
    )

    return out


def draw_demo_frame(
    count: int,
    area_name: str,
    last_publish_time: float,
    width: int = 640,
    height: int = 480,
) -> np.ndarray:
    """Build a synthetic demo frame (no real camera) with the overlay applied."""
    from models.people_detector import DetectionFrame, classify_status, status_color as sc

    frame = np.full((height, width, 3), (30, 30, 30), dtype=np.uint8)

    # Fake people silhouettes so it doesn't look completely empty
    for i in range(count):
        cx = 80 + (i % 5) * 110
        cy = 180 + (i // 5) * 100
        cv2.ellipse(frame, (cx, cy - 28), (18, 22), 0, 0, 360, (70, 70, 70), -1)
        cv2.rectangle(frame, (cx - 22, cy - 6), (cx + 22, cy + 55), (70, 70, 70), -1)

    s = classify_status(count)
    det = DetectionFrame(
        count=count,
        status=s,
        color=sc(s),
        tracks_in_roi=[],
        tracks_outside_roi=[],
    )
    return draw_frame(frame, det, area_name, roi=None, last_publish_time=last_publish_time)
