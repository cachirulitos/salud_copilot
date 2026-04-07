import json
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_ENV = str(Path(__file__).parent.parent.parent / ".env")


class CVSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ROOT_ENV,
        case_sensitive=False,
        extra="ignore",
    )

    api_base_url: str = "http://localhost:8000"
    internal_cv_token: str = "saludcopilot-internal-token-change-in-prod"
    camera_index: int = 0
    capture_interval_seconds: int = 5
    yolo_model_name: str = "yolov8n.pt"
    confidence_threshold: float = 0.4
    # ROI as "x1,y1,x2,y2" in pixels — empty string means full frame
    camera_roi: str = ""
    camera_to_area_mapping: str = "{}"

    @property
    def roi_rect(self) -> tuple[int, int, int, int] | None:
        """Parse CAMERA_ROI into a (x1, y1, x2, y2) tuple, or None if unset."""
        if not self.camera_roi.strip():
            return None
        x1, y1, x2, y2 = (int(v) for v in self.camera_roi.split(","))
        return (x1, y1, x2, y2)

    @property
    def area_mapping(self) -> dict:
        """Parse the JSON camera-to-area mapping from the env string."""
        return json.loads(self.camera_to_area_mapping)


settings = CVSettings()
