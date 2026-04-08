"""
Train the wait-time model using real Salud Digna data from the Excel file.

Reads three sheets from the hackathon Excel, normalises column names and
study-type IDs to match the inference API, then trains and saves artifacts.

Usage (from project root):
    cd ml
    python scripts/train_real.py

Output: ml/artifacts/model.pkl  ml/artifacts/encodings.pkl
"""

import logging
import sys
import os
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from feature_engineering import build_training_features
from train import train_model, save_artifacts

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

EXCEL_PATH = Path(__file__).parent.parent.parent / "resources" / "Recursos Hackthon 2026.xlsx"

# Maps IdEstudio integer → study_type string used by the API at inference time.
# Only IDs that exist in clinical_areas are included; others are kept as-is
# so the model still learns from all available data.
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


def load_excel_sheets(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read the three sheets needed for training and normalise column names."""
    logger.info("Reading Excel: %s", path)
    xl = pd.ExcelFile(path)

    # ── Ventas ────────────────────────────────────────────────────────────
    ventas = xl.parse("Ventas")
    ventas = ventas.rename(columns={
        "IdSucursal":   "idSucursal",
        "IdEstudio":    "idEstudio",
        "IdPaciente":   "idPaciente",
        "FechaServicio": "FechaServicio",
        "Estatus":      "Estatus",
        "IdReservacion": "idReservacion",
    })
    # Map integer study IDs to normalised strings so encoding matches inference
    ventas["idEstudio"] = ventas["idEstudio"].map(
        lambda x: STUDY_ID_TO_TYPE.get(x, f"estudio_{x}")
    )
    logger.info("Ventas: %d rows, %d clinics", len(ventas), ventas["idSucursal"].nunique())

    # ── Promedios de espera ───────────────────────────────────────────────
    promedios = xl.parse("Promedios Espera")
    promedios = promedios.rename(columns={
        "IdSucursal": "idSucursal",
        "IdEstudio":  "idEstudio",
        "Promedio":   "promedio_minutos",
    })
    promedios["idEstudio"] = promedios["idEstudio"].map(
        lambda x: STUDY_ID_TO_TYPE.get(x, f"estudio_{x}")
    )
    # Keep only the most recent average per (clinic, study)
    if "Fecha" in promedios.columns:
        promedios = (
            promedios.sort_values("Fecha")
            .groupby(["idSucursal", "idEstudio"], as_index=False)
            .last()
        )
    logger.info("Promedios: %d rows", len(promedios))

    # ── Consultorios ──────────────────────────────────────────────────────
    consultorios = xl.parse("Consultorios x Clinica")
    consultorios = consultorios.rename(columns={
        "IdSucursal":          "idSucursal",
        "IdEstudio":           "idEstudio",
        "CantidadConsultorios": "capacidad_simultanea",
    })
    consultorios["idEstudio"] = consultorios["idEstudio"].map(
        lambda x: STUDY_ID_TO_TYPE.get(x, f"estudio_{x}")
    )
    logger.info("Consultorios: %d rows", len(consultorios))

    return ventas, promedios, consultorios


if __name__ == "__main__":
    if not EXCEL_PATH.exists():
        logger.error("Excel no encontrado: %s", EXCEL_PATH)
        sys.exit(1)

    ventas, promedios, consultorios = load_excel_sheets(EXCEL_PATH)

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
    print("MODELO ENTRENADO CON DATOS REALES")
    print("================================")
    print(f"Filas de entrenamiento : {len(features_df):,}")
    print(f"MAE                    : {metrics['mae']:.1f} min")
    print(f"R²                     : {metrics['r2']:.3f}")
    print(f"Tipos de estudio       : {sorted(encoding_maps['study_type'].keys())}")
    print(f"Clínicas               : {len(encoding_maps['clinic'])}")
    print("Artifacts guardados en ml/artifacts/")
    print("================================\n")
