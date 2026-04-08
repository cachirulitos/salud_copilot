import logging
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from feature_engineering import FEATURE_COLUMNS

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent / "artifacts"

HYPERPARAMETERS = {
    "n_estimators": 100,
    "max_depth": None,
    "min_samples_split": 2,
    "random_state": 42,
    "n_jobs": -1,
}

TEST_SIZE = 0.2
RANDOM_STATE = 42


def train_model(features_df: pd.DataFrame) -> tuple[RandomForestRegressor, dict]:
    """Train a RandomForest on the feature matrix and return model + metrics."""
    X = features_df[FEATURE_COLUMNS]
    y = features_df["waiting_time_minutes"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    model = RandomForestRegressor(**HYPERPARAMETERS)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    print(
        f"MAE: {mae:.1f} min | R2: {r2:.2f} "
        f"| Train: {len(X_train)} | Test: {len(X_test)}"
    )

    return model, {"mae": mae, "r2": r2}


def save_artifacts(
    model: RandomForestRegressor,
    encoding_maps: dict,
    output_dir: Path = MODEL_DIR,
) -> None:
    """Persist the trained model and encoding maps to disk."""
    output_dir.mkdir(exist_ok=True)
    joblib.dump(model, output_dir / "model.pkl")
    joblib.dump(encoding_maps, output_dir / "encodings.pkl")
    logger.info("Artifacts saved to %s", output_dir)


def load_artifacts(model_dir: Path = MODEL_DIR) -> tuple[RandomForestRegressor, dict]:
    """Load trained model and encoding maps from disk."""
    model = joblib.load(model_dir / "model.pkl")
    encoding_maps = joblib.load(model_dir / "encodings.pkl")
    return model, encoding_maps
