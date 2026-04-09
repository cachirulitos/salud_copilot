import asyncio
import logging
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import select

_ml_docker = Path("/ml/src")
_ml_local = Path(__file__).resolve().parent.parent.parent.parent.parent / "ml" / "src"
_ML_SRC = str(_ml_docker) if _ml_docker.exists() else str(_ml_local)
if _ML_SRC not in sys.path:
    sys.path.insert(0, _ML_SRC)

from feature_engineering import FEATURE_COLUMNS  # noqa: E402
from train import HYPERPARAMETERS, MODEL_DIR, save_artifacts  # noqa: E402

from app.core.database import AsyncSessionLocal
from app.models.models import ClinicalArea, Visit, VisitStep, VisitStepStatus

logger = logging.getLogger(__name__)


async def collect_training_data(db, days: int = 30) -> pd.DataFrame:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(VisitStep, ClinicalArea, Visit)
        .join(ClinicalArea, VisitStep.clinical_area_id == ClinicalArea.id)
        .join(Visit, VisitStep.visit_id == Visit.id)
        .where(
            VisitStep.status == VisitStepStatus.COMPLETED,
            VisitStep.actual_wait_minutes.isnot(None),
            VisitStep.started_at >= cutoff,
        )
    )
    rows = result.all()

    if not rows:
        return pd.DataFrame()

    records = []
    for step, area, visit in rows:
        started = step.started_at
        if started is None:
            continue
        records.append({
            "hour_of_day": started.hour,
            "day_of_week": started.weekday(),
            "is_weekend": int(started.weekday() >= 5),
            "study_type_id": area.study_type,
            "clinic_id": str(area.clinic_id),
            "simultaneous_capacity": area.simultaneous_capacity,
            "current_queue_length": max(0, step.step_order - 1),
            "has_appointment": int(visit.has_appointment),
            "waiting_time_minutes": step.actual_wait_minutes,
        })

    return pd.DataFrame(records)


async def calculate_rmse(db, predictor) -> dict[str, float]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(
        select(VisitStep, ClinicalArea, Visit)
        .join(ClinicalArea, VisitStep.clinical_area_id == ClinicalArea.id)
        .join(Visit, VisitStep.visit_id == Visit.id)
        .where(
            VisitStep.status == VisitStepStatus.COMPLETED,
            VisitStep.actual_wait_minutes.isnot(None),
            VisitStep.started_at >= cutoff,
        )
    )
    rows = result.all()

    errors: dict[str, list[float]] = {}
    for step, area, visit in rows:
        started = step.started_at
        if started is None:
            continue

        try:
            predicted = predictor.predict_wait_minutes(
                hour_of_day=started.hour,
                day_of_week=started.weekday(),
                study_type_raw_id=area.study_type,
                clinic_raw_id=str(area.clinic_id),
                simultaneous_capacity=area.simultaneous_capacity,
                current_queue_length=max(0, step.step_order - 1),
                has_appointment=visit.has_appointment,
            )
        except Exception:
            logger.exception("predict_wait_minutes failed for step %s", step.id)
            continue

        diff = predicted - step.actual_wait_minutes
        errors.setdefault(area.study_type, []).append(diff * diff)

    return {
        study_type: math.sqrt(sum(sq) / len(sq))
        for study_type, sq in errors.items()
        if sq
    }


async def check_and_retrain(threshold_rmse: float = 8.0) -> None:
    try:
        from app.core.predictor_client import get_predictor
        predictor = get_predictor()
        if predictor is None:
            logger.warning("retraining_service: predictor not loaded, skipping RMSE check")
            return

        async with AsyncSessionLocal() as db:
            rmse_before = await calculate_rmse(db, predictor)

        if not rmse_before:
            logger.info("retraining_service: no evaluation data available, skipping")
            return

        for study_type, rmse in rmse_before.items():
            logger.info("retraining_service: RMSE[%s] = %.2f min", study_type, rmse)

        needs_retrain = any(v > threshold_rmse for v in rmse_before.values())
        if not needs_retrain:
            logger.info(
                "retraining_service: all RMSE values within threshold (%.1f), no retraining needed",
                threshold_rmse,
            )
            return

        worst = max(rmse_before, key=lambda k: rmse_before[k])
        logger.info(
            "retraining_service: RMSE threshold exceeded (worst: %s = %.2f), starting retraining",
            worst,
            rmse_before[worst],
        )

        async with AsyncSessionLocal() as db:
            df = await collect_training_data(db, days=30)

        if df.empty or len(df) < 50:
            logger.warning(
                "retraining_service: insufficient training data (%d rows), skipping", len(df)
            )
            return

        logger.info("retraining_service: training on %d rows", len(df))
        logger.info("retraining_service: dtypes\n%s", df.dtypes.to_string())
        logger.info("retraining_service: nulls\n%s", df.isnull().sum().to_string())

        from sklearn.ensemble import RandomForestRegressor

        # Encode string columns to integers before fitting
        study_encoding = {v: i for i, v in enumerate(df["study_type_id"].unique())}
        clinic_encoding = {v: i for i, v in enumerate(df["clinic_id"].unique())}
        df = df.copy()
        df["study_type_id"] = df["study_type_id"].map(study_encoding)
        df["clinic_id"] = df["clinic_id"].map(clinic_encoding)

        # Coerce all feature columns to numeric and drop any remaining nulls
        for col in FEATURE_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=FEATURE_COLUMNS + ["waiting_time_minutes"])

        if len(df) < 50:
            logger.warning(
                "retraining_service: insufficient training data after cleaning (%d rows), skipping", len(df)
            )
            return

        X = df[FEATURE_COLUMNS]
        y = df["waiting_time_minutes"]
        new_model = RandomForestRegressor(**HYPERPARAMETERS)
        new_model.fit(X, y)

        new_encoding_maps = {"study_type": study_encoding, "clinic": clinic_encoding}

        save_artifacts(new_model, new_encoding_maps, MODEL_DIR)
        logger.info("retraining_service: new artifacts saved to %s", MODEL_DIR)

        predictor.model = new_model
        predictor.encoding_maps = new_encoding_maps
        predictor._study_median_cache = {}

        # Reload singleton so the new artifacts are picked up cleanly
        import app.core.predictor_client as _pc
        _pc._predictor = None
        predictor = _pc.get_predictor()

        async with AsyncSessionLocal() as db:
            rmse_after = await calculate_rmse(db, predictor)

        for study_type, rmse in rmse_after.items():
            before = rmse_before.get(study_type, float("nan"))
            logger.info(
                "retraining_service: RMSE[%s] %.2f → %.2f min", study_type, before, rmse
            )

    except Exception:
        logger.exception("retraining_service: unhandled error in check_and_retrain")


async def run_retraining_monitor(interval_seconds: int = 604800) -> None:
    while True:
        try:
            await check_and_retrain()
        except Exception:
            logger.exception("retraining_service: run_retraining_monitor error")
        await asyncio.sleep(interval_seconds)
