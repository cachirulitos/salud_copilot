import logging
from pathlib import Path

from feature_engineering import extract_inference_features
from train import MODEL_DIR, load_artifacts

logger = logging.getLogger(__name__)

MINIMUM_WAIT_MINUTES = 1


class WaitTimePredictor:
    """Load trained artifacts and serve wait time predictions."""

    def __init__(self, model_dir: Path = MODEL_DIR) -> None:
        self.model, self.encoding_maps = load_artifacts(model_dir)
        self._median_fallback: int | None = None

    def predict_wait_minutes(
        self,
        hour_of_day: int,
        day_of_week: int,
        study_type_raw_id,
        clinic_raw_id,
        simultaneous_capacity: int,
        current_queue_length: int,
        has_appointment: bool,
    ) -> int:
        """Return predicted wait time in minutes, falling back to median on unknown labels."""
        features = extract_inference_features(
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            study_type_raw_id=study_type_raw_id,
            clinic_raw_id=clinic_raw_id,
            simultaneous_capacity=simultaneous_capacity,
            current_queue_length=current_queue_length,
            has_appointment=has_appointment,
            encoding_maps=self.encoding_maps,
        )

        has_unknown_label = features.isnull().any().any()
        if has_unknown_label:
            if self._median_fallback is not None:
                logger.warning(
                    "Unknown label for study_type=%s or clinic=%s — using median fallback %d min",
                    study_type_raw_id,
                    clinic_raw_id,
                    self._median_fallback,
                )
                return self._median_fallback
            logger.warning("Unknown label and no median fallback available — returning minimum")
            return MINIMUM_WAIT_MINUTES

        raw_prediction = self.model.predict(features)[0]
        return max(MINIMUM_WAIT_MINUTES, round(int(raw_prediction)))

    def set_median_fallback(self, median_minutes: int) -> None:
        """Set the fallback value used when an unknown label is encountered."""
        self._median_fallback = median_minutes

    @property
    def is_ready(self) -> bool:
        """Return True if the model artifacts are loaded."""
        return self.model is not None
