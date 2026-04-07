from dataclasses import dataclass, field
import numpy as np

PERSON_CLASS_ID = 0
THRESHOLD_WARNING = 4
THRESHOLD_SATURATED = 8

# BGR colors
COLOR_NORMAL      = (80, 200, 80)
COLOR_WARNING     = (0, 165, 255)
COLOR_SATURATED   = (0, 0, 220)
COLOR_OUTSIDE_ROI = (100, 100, 100)


def classify_status(count: int) -> str:
    if count >= THRESHOLD_SATURATED:
        return "saturated"
    if count >= THRESHOLD_WARNING:
        return "warning"
    return "normal"


def status_color(status: str) -> tuple[int, int, int]:
    return {
        "normal": COLOR_NORMAL,
        "warning": COLOR_WARNING,
        "saturated": COLOR_SATURATED,
    }.get(status, COLOR_NORMAL)


def point_in_roi(cx: float, cy: float, roi: tuple[int, int, int, int]) -> bool:
    x1, y1, x2, y2 = roi
    return x1 <= cx <= x2 and y1 <= cy <= y2


@dataclass
class DetectionFrame:
    count: int
    status: str
    color: tuple[int, int, int]
    tracks_in_roi: list = field(default_factory=list)
    tracks_outside_roi: list = field(default_factory=list)


class PeopleDetector:
    """
    Detecta personas con inferencia simple (sin tracker).
    - conf aplicado en inferencia, no en post-filtro
    - ROI por centro de caja
    - Compatible con main.py: expone detect() y count_people_with_annotated_frame()
    """

    def __init__(self, model_name: str, confidence_threshold: float) -> None:
        from ultralytics import YOLO
        import torch

        original_load = torch.load

        def custom_load(*args, **kwargs):
            kwargs["weights_only"] = False
            return original_load(*args, **kwargs)

        torch.load = custom_load
        try:
            self.model = YOLO(model_name)
        finally:
            torch.load = original_load

        self.confidence_threshold = confidence_threshold

    def detect(
        self,
        frame: np.ndarray,
        roi: tuple[int, int, int, int] | None = None,
    ) -> DetectionFrame:
        """
        Método principal usado por main.py.
        Retorna DetectionFrame con conteo, estado y cajas separadas por ROI.
        """
        results = self.model(
            frame,
            verbose=False,
            classes=[PERSON_CLASS_ID],
            conf=self.confidence_threshold,  # filtro aplicado en inferencia
        )

        in_roi: list = []
        outside_roi: list = []

        boxes = results[0].boxes
        if boxes is not None and len(boxes) > 0:
            for box in boxes:
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
                cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                entry = (x1, y1, x2, y2, -1)  # -1 = sin track_id

                if roi is None or point_in_roi(cx, cy, roi):
                    in_roi.append(entry)
                else:
                    outside_roi.append(entry)

        count = len(in_roi)
        s = classify_status(count)
        return DetectionFrame(
            count=count,
            status=s,
            color=status_color(s),
            tracks_in_roi=in_roi,
            tracks_outside_roi=outside_roi,
        )

    def count_people_with_annotated_frame(
        self, frame: np.ndarray
    ) -> tuple[int, np.ndarray]:
        """Legacy: usado si algo llama a este método directamente."""
        detection = self.detect(frame)
        results = self.model(
            frame,
            verbose=False,
            classes=[PERSON_CLASS_ID],
            conf=self.confidence_threshold,
        )
        return detection.count, results[0].plot()