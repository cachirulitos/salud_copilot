"""
Train the wait-time model pulling data directly from the PostgreSQL Database.

Reads from ventas, promedios_espera, and consultorios_por_clinica, mapping columns
to match the expectation of the feature engineering layer.
"""

import logging
import sys
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from feature_engineering import build_training_features
from train import train_model, save_artifacts

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Load .env from root
DOTENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=DOTENV_PATH)

DATABASE_URL = os.environ.get("ML_DATABASE_URL") or os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL no está definida en el archivo .env")
    sys.exit(1)

# El string normal para SQLAlchemy si empieza con postgres:// debe ser postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Forzar driver síncrono (psycopg2) porque pandas read_sql es síncrono
if "asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

STUDY_ID_TO_TYPE = {
    1:  "densitometria",
    2:  "laboratorio",
    3:  "mastografia",
    4:  "papanicolaou",
    5:  "rayos_x",
    6:  "ultrasonido",
    9:  "electrocardiograma",
    11: "tomografia",
    12: "resonancia",
    16: "nutricion",
}

def load_data_from_db(engine) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    logger.info("Loading data from database...")
    
    # ── Ventas ────────────────────────────────────────────────────────────
    ventas_query = """
        SELECT 
            id_sucursal AS "idSucursal",
            id_estudio AS "idEstudio",
            id_paciente AS "idPaciente",
            fecha_servicio AS "FechaServicio",
            id_estatus AS "Estatus",
            id_reservacion AS "idReservacion"
        FROM ventas;
    """
    ventas = pd.read_sql(ventas_query, engine)
    
    ventas["idEstudio"] = ventas["idEstudio"].map(
        lambda x: STUDY_ID_TO_TYPE.get(x, f"estudio_{x}")
    )
    # pandas datetime mapping
    ventas["FechaServicio"] = pd.to_datetime(ventas["FechaServicio"])
    logger.info("Ventas: %d rows", len(ventas))

    # ── Promedios de espera ───────────────────────────────────────────────
    promedios_query = """
        SELECT
            id_sucursal AS "idSucursal",
            id_estudio AS "idEstudio",
            promedio AS "promedio_minutos",
            fecha
        FROM promedios_espera
        ORDER BY fecha ASC;
    """
    promedios = pd.read_sql(promedios_query, engine)
    promedios["idEstudio"] = promedios["idEstudio"].map(
        lambda x: STUDY_ID_TO_TYPE.get(x, f"estudio_{x}")
    )
    # Keep only the most recent average per (clinic, study)
    if "fecha" in promedios.columns:
        promedios = (
            promedios.groupby(["idSucursal", "idEstudio"], as_index=False)
            .last()
        )
    logger.info("Promedios: %d rows", len(promedios))

    # ── Consultorios ──────────────────────────────────────────────────────
    consultorios_query = """
        SELECT
            id_sucursal AS "idSucursal",
            id_estudio AS "idEstudio",
            cantidad AS "capacidad_simultanea"
        FROM consultorios_por_clinica;
    """
    consultorios = pd.read_sql(consultorios_query, engine)
    consultorios["idEstudio"] = consultorios["idEstudio"].map(
        lambda x: STUDY_ID_TO_TYPE.get(x, f"estudio_{x}")
    )
    logger.info("Consultorios: %d rows", len(consultorios))

    return ventas, promedios, consultorios

if __name__ == "__main__":
    masked_url = DATABASE_URL
    if "@" in masked_url:
        masked_url = masked_url.replace(masked_url.split("@")[0].split("://")[1], "***")
    logger.info("Connecting to Database: %s", masked_url)
    
    engine = create_engine(DATABASE_URL)
    
    try:
        ventas, promedios, consultorios = load_data_from_db(engine)
    except Exception as e:
        logger.error("Error al extraer datos: %s", str(e))
        sys.exit(1)

    logger.info("Building feature matrix...")
    features_df, encoding_maps = build_training_features(ventas, promedios, consultorios)
    logger.info(
        "Features: %d rows | study_types: %s",
        len(features_df),
        list(encoding_maps["study_type"].keys()),
    )

    logger.info("Training model...")
    model, metrics = train_model(features_df)

    logger.info("Saving artifacts...")
    save_artifacts(model, encoding_maps)

    print("\n================================")
    print("MODELO ENTRENADO DESDE POSTGRESQL")
    print("================================")
    print(f"Filas de entrenamiento : {len(features_df):,}")
    print(f"MAE                    : {metrics['mae']:.1f} min")
    print(f"R²                     : {metrics['r2']:.3f}")
    if "study_type" in encoding_maps:
        print(f"Tipos de estudio       : {sorted(encoding_maps['study_type'].keys())}")
    if "clinic" in encoding_maps:
        print(f"Clínicas               : {len(encoding_maps['clinic'])}")
    print("Artifacts guardados en ml/artifacts/")
    print("================================\n")
