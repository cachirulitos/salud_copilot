"""
Generate synthetic training data and train the wait time model.

Simulates realistic Salud Digna wait times based on:
- Hour of day (morning peak 8-11am, afternoon trough 2-4pm)
- Day of week (weekdays busier than weekends)
- Study type (each has a different base duration)
- Queue length (more people = longer wait)

Usage:
    cd ml
    python scripts/train_synthetic.py

Outputs: ml/artifacts/model.pkl, ml/artifacts/encodings.pkl
"""
import sys
import os
import random
import logging

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from feature_engineering import build_training_features
from train import train_model, save_artifacts

logging.basicConfig(level=logging.INFO)

# Known clinic UUID from seed data
CLINIC_ID = "1db93003-d50e-4f56-80d0-8b994b98eaa8"

# Base wait minutes per study type (matches BASE_WAIT_TIMES in areas.py)
STUDY_BASE_MINUTES = {
    "laboratorio":        15,
    "ultrasonido":        20,
    "rayos_x":            12,
    "electrocardiograma":  8,
    "papanicolaou":       10,
    "densitometria":      15,
    "tomografia":         25,
}

STUDY_CAPACITY = {
    "laboratorio":        3,
    "ultrasonido":        2,
    "rayos_x":            2,
    "electrocardiograma": 1,
    "papanicolaou":       2,
    "densitometria":      1,
    "tomografia":         1,
}

N_ROWS = 3000
RANDOM_SEED = 42


def _hour_multiplier(hour: int) -> float:
    """Return a wait time multiplier based on hour of day.

    Peak: 8-11am (1.6x). Normal: 11am-2pm (1.0x).
    Quiet: 2-5pm (0.7x). Evening: 5-8pm (1.2x).
    """
    if 8 <= hour < 11:
        return 1.6
    if 11 <= hour < 14:
        return 1.0
    if 14 <= hour < 17:
        return 0.7
    if 17 <= hour < 20:
        return 1.2
    return 0.5


def _day_multiplier(day_of_week: int) -> float:
    """Mondays and Fridays slightly busier; weekends much quieter."""
    multipliers = {0: 1.3, 1: 1.1, 2: 1.0, 3: 1.0, 4: 1.2, 5: 0.6, 6: 0.4}
    return multipliers[day_of_week]


def generate_synthetic_rows(n: int) -> list[dict]:
    rng = np.random.default_rng(RANDOM_SEED)
    rows = []

    study_types = list(STUDY_BASE_MINUTES.keys())

    for _ in range(n):
        study_type = rng.choice(study_types)
        hour = int(rng.integers(7, 20))
        day = int(rng.integers(0, 7))
        has_appointment = bool(rng.random() < 0.35)
        queue_sim = int(rng.integers(0, 10))

        base = STUDY_BASE_MINUTES[study_type]
        noise = rng.normal(0, base * 0.15)
        wait = (
            base
            * _hour_multiplier(hour)
            * _day_multiplier(day)
            + queue_sim * 2.5
            + noise
            - (3 if has_appointment else 0)
        )
        wait = max(1.0, round(float(wait), 1))

        # Simulate a timestamp with the generated hour/day
        # Use a Monday=2025-01-06 as anchor, offset by day
        from datetime import datetime, timedelta
        anchor = datetime(2025, 1, 6)  # Monday
        day_offset = timedelta(days=day)
        ts = anchor + day_offset
        ts = ts.replace(hour=hour, minute=int(rng.integers(0, 60)))

        rows.append({
            "idSucursal": CLINIC_ID,
            "idEstudio": study_type,
            "idPaciente": f"PAC-{rng.integers(1000, 9999)}",
            "FechaServicio": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "Estatus": "Atendido",
            "idReservacion": f"RES-{rng.integers(100, 999)}" if has_appointment else None,
            "_wait_minutes": wait,
        })

    return rows


def build_promedios(rows: list[dict]) -> pd.DataFrame:
    """Compute average wait per (study_type, clinic) for the promedios table."""
    df = pd.DataFrame(rows)
    promedios = (
        df.groupby(["idEstudio", "idSucursal"])["_wait_minutes"]
        .mean()
        .reset_index()
        .rename(columns={"_wait_minutes": "promedio_minutos"})
    )
    return promedios


def build_consultorios() -> pd.DataFrame:
    rows = [
        {"idEstudio": st, "idSucursal": CLINIC_ID, "capacidad_simultanea": cap}
        for st, cap in STUDY_CAPACITY.items()
    ]
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("Generating synthetic training data...")
    rows = generate_synthetic_rows(N_ROWS)

    ventas_df = pd.DataFrame(rows).drop(columns=["_wait_minutes"])
    ventas_df["FechaServicio"] = pd.to_datetime(ventas_df["FechaServicio"])

    promedios_df = build_promedios(rows)
    consultorios_df = build_consultorios()

    print(f"  ventas: {len(ventas_df)} rows")
    print(f"  promedios: {len(promedios_df)} rows")
    print(f"  consultorios: {len(consultorios_df)} rows")

    print("Building feature matrix...")
    features_df, encoding_maps = build_training_features(ventas_df, promedios_df, consultorios_df)
    print(f"  features: {len(features_df)} rows, {len(features_df.columns)} columns")

    print("Training model...")
    model, metrics = train_model(features_df)

    print("Saving artifacts...")
    save_artifacts(model, encoding_maps)

    print("\n=== TRAINING COMPLETE ===")
    print(f"MAE: {metrics['mae']:.1f} min | R2: {metrics['r2']:.2f}")
    print("Artifacts saved to ml/artifacts/")
    print("  model.pkl")
    print("  encodings.pkl")
    print("=========================\n")
