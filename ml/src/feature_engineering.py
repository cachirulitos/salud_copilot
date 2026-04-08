import logging

import pandas as pd

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "study_type_id",
    "clinic_id",
    "simultaneous_capacity",
    "current_queue_length",
    "has_appointment",
]

WEEKEND_DAY_START = 5


def build_training_features(
    ventas: pd.DataFrame,
    promedios: pd.DataFrame,
    consultorios: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """Build the feature matrix and encoding maps from raw dataframes.

    Returns:
        features_df: DataFrame with FEATURE_COLUMNS + 'waiting_time_minutes'
        encoding_maps: dict with 'study_type' and 'clinic' label encodings
    """
    ventas = ventas.copy()

    ventas["hour_of_day"] = ventas["FechaServicio"].dt.hour
    ventas["day_of_week"] = ventas["FechaServicio"].dt.dayofweek
    ventas["is_weekend"] = (ventas["day_of_week"] >= WEEKEND_DAY_START).astype(int)
    ventas["has_appointment"] = ventas["idReservacion"].notna().astype(int)
    ventas["current_queue_length"] = 0

    study_encoding = {value: index for index, value in enumerate(ventas["idEstudio"].unique())}
    clinic_encoding = {value: index for index, value in enumerate(ventas["idSucursal"].unique())}
    ventas["study_type_id"] = ventas["idEstudio"].map(study_encoding)
    ventas["clinic_id"] = ventas["idSucursal"].map(clinic_encoding)

    merged = ventas.merge(
        consultorios[["idEstudio", "idSucursal", "capacidad_simultanea"]],
        on=["idEstudio", "idSucursal"],
        how="left",
    )
    merged = merged.merge(
        promedios[["idEstudio", "idSucursal", "promedio_minutos"]],
        on=["idEstudio", "idSucursal"],
        how="left",
    )

    merged.rename(
        columns={
            "capacidad_simultanea": "simultaneous_capacity",
            "promedio_minutos": "waiting_time_minutes",
        },
        inplace=True,
    )

    merged["simultaneous_capacity"] = merged["simultaneous_capacity"].fillna(1)
    merged["waiting_time_minutes"] = merged["waiting_time_minutes"].fillna(
        merged["waiting_time_minutes"].median()
    )

    features_df = merged[FEATURE_COLUMNS + ["waiting_time_minutes"]].dropna()
    encoding_maps = {"study_type": study_encoding, "clinic": clinic_encoding}
    return features_df, encoding_maps


def extract_inference_features(
    hour_of_day: int,
    day_of_week: int,
    study_type_raw_id,
    clinic_raw_id,
    simultaneous_capacity: int,
    current_queue_length: int,
    has_appointment: bool,
    encoding_maps: dict,
) -> pd.DataFrame:
    """Build a single-row DataFrame for model inference using the trained encoding maps."""
    study_type_id = encoding_maps["study_type"].get(study_type_raw_id)
    clinic_id = encoding_maps["clinic"].get(clinic_raw_id)

    if study_type_id is None:
        logger.warning("Unknown study_type_raw_id '%s' — encoding will be None", study_type_raw_id)
    if clinic_id is None:
        logger.warning("Unknown clinic_raw_id '%s' — encoding will be None", clinic_raw_id)

    row = {
        "hour_of_day": hour_of_day,
        "day_of_week": day_of_week,
        "is_weekend": int(day_of_week >= WEEKEND_DAY_START),
        "study_type_id": study_type_id,
        "clinic_id": clinic_id,
        "simultaneous_capacity": simultaneous_capacity,
        "current_queue_length": current_queue_length,
        "has_appointment": int(has_appointment),
    }
    return pd.DataFrame([row], columns=FEATURE_COLUMNS)
