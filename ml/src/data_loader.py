import logging

import pandas as pd

logger = logging.getLogger(__name__)

VENTAS_REQUIRED_COLUMNS = [
    "idSucursal", "idEstudio", "idPaciente",
    "FechaServicio", "Estatus", "idReservacion",
]

PROMEDIOS_REQUIRED_COLUMNS = ["idEstudio", "idSucursal", "promedio_minutos"]

CONSULTORIOS_REQUIRED_COLUMNS = ["idEstudio", "idSucursal", "capacidad_simultanea"]


def validate_dataframe(dataframe: pd.DataFrame, required_columns: list[str], name: str) -> None:
    """Log shape and null counts for required columns. Raise if a column is missing."""
    logger.info("%s shape: %s", name, dataframe.shape)
    for column in required_columns:
        if column not in dataframe.columns:
            raise ValueError(f"Missing required column '{column}' in {name}")
        null_count = dataframe[column].isnull().sum()
        logger.info("%s — %s nulls: %d", name, column, null_count)


def load_ventas(filepath: str) -> pd.DataFrame:
    """Load the ventas CSV, parse FechaServicio as datetime, and validate required columns."""
    dataframe = pd.read_csv(filepath)
    dataframe["FechaServicio"] = pd.to_datetime(dataframe["FechaServicio"])

    has_time_component = (
        dataframe["FechaServicio"].dt.hour.sum() > 0
        or dataframe["FechaServicio"].dt.minute.sum() > 0
    )
    if not has_time_component:
        logger.warning(
            "FechaServicio appears to contain only dates with no time component. "
            "Hour-of-day features will be zero."
        )

    validate_dataframe(dataframe, VENTAS_REQUIRED_COLUMNS, "ventas")
    return dataframe


def load_promedios_espera(filepath: str) -> pd.DataFrame:
    """Load the wait time averages CSV and validate required columns."""
    dataframe = pd.read_csv(filepath)
    validate_dataframe(dataframe, PROMEDIOS_REQUIRED_COLUMNS, "promedios_espera")
    return dataframe


def load_consultorios(filepath: str) -> pd.DataFrame:
    """Load the consulting rooms CSV with capacity data and validate required columns."""
    dataframe = pd.read_csv(filepath)
    validate_dataframe(dataframe, CONSULTORIOS_REQUIRED_COLUMNS, "consultorios")
    return dataframe
