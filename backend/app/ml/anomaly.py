import pickle
from pathlib import Path

import pandas as pd
from sklearn.ensemble import IsolationForest

from app.models.air_quality import AirQualityReading

_MODELS_DIR = Path(__file__).parent.parent.parent / "models"

# No lag features — anomaly detection scores a single reading in isolation
ANOMALY_FEATURE_COLS = [
    "aqi", "pm25", "pm10", "co", "no2", "so2", "o3",
    "hour", "day_of_week", "month",
]


def _model_path(location_id: str) -> Path:
    return _MODELS_DIR / f"{location_id}_anomaly.pkl"


def train_anomaly_model(location_id: str, df: pd.DataFrame) -> IsolationForest:
    """Fit IsolationForest on the feature DataFrame and persist it to disk."""
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["month"] = df["timestamp"].dt.month

    X = df[ANOMALY_FEATURE_COLS].fillna(0.0)

    model = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
    model.fit(X)

    path = _model_path(location_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)

    return model


def load_anomaly_model(location_id: str) -> IsolationForest:
    path = _model_path(location_id)
    if not path.exists():
        raise FileNotFoundError(
            f"No anomaly model for location '{location_id}'. Run training first."
        )
    with open(path, "rb") as f:
        return pickle.load(f)


def detect_anomaly(location_id: str, reading: AirQualityReading) -> bool:
    """Return True if the reading is flagged as anomalous by the trained model."""
    try:
        model = load_anomaly_model(location_id)
    except FileNotFoundError:
        return False

    ts = pd.Timestamp(reading.timestamp)
    features = {
        "aqi": float(reading.aqi),
        "pm25": float(reading.pm25 or 0.0),
        "pm10": float(reading.pm10 or 0.0),
        "co": float(reading.co or 0.0),
        "no2": float(reading.no2 or 0.0),
        "so2": float(reading.so2 or 0.0),
        "o3": float(reading.o3 or 0.0),
        "hour": ts.hour,
        "day_of_week": ts.dayofweek,
        "month": ts.month,
    }

    X = pd.DataFrame([features])[ANOMALY_FEATURE_COLS]
    prediction = model.predict(X)[0]  # 1 = normal, -1 = anomaly
    return prediction == -1
