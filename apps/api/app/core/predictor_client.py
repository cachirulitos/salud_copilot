import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_ml_docker = Path("/ml/src")
_ml_local = Path(__file__).parent.parent.parent.parent.parent / "ml" / "src"
_ML_SRC = str(_ml_docker) if _ml_docker.exists() else str(_ml_local)

sys.path.insert(0, _ML_SRC)

_predictor = None


def get_predictor():
    """Return the singleton WaitTimePredictor, loading artifacts on first call."""
    global _predictor
    if _predictor is None:
        try:
            from predictor import WaitTimePredictor  # noqa: PLC0415

            _predictor = WaitTimePredictor()
            logger.info("ML predictor loaded successfully")
        except Exception as exc:
            logger.error("Failed to load ML predictor: %s — falling back to placeholder", exc)
            _predictor = None
    return _predictor
