import pickle
from pathlib import Path

import pandas as pd
from xgboost import XGBRegressor

FEATURE_COLS = [
    "pm25",
    "pm10",
    "co",
    "no2",
    "so2",
    "o3",
    "aqi_lag_1h",
    "aqi_lag_3h",
    "aqi_lag_24h",
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
]

_MODELS_DIR = Path(__file__).parent.parent.parent / "models"


def _model_path(location_id: str) -> Path:
    return _MODELS_DIR / f"{location_id}_forecast.pkl"


def train_model(location_id: str, df: pd.DataFrame) -> XGBRegressor:
    """Fit an XGBRegressor on the feature DataFrame and persist it to disk."""
    X = df[FEATURE_COLS]
    y = df["aqi"]

    model = XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )
    model.fit(X, y)

    path = _model_path(location_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)

    return model


def load_model(location_id: str) -> XGBRegressor:
    path = _model_path(location_id)
    if not path.exists():
        raise FileNotFoundError(
            f"No forecast model for location '{location_id}'. Run training first."
        )
    with open(path, "rb") as f:
        return pickle.load(f)


def predict_next_24h(location_id: str, df: pd.DataFrame) -> list[dict]:
    """Recursively forecast AQI for the next 24 hours.

    Uses the last row of df as the starting point. Predicted values feed back
    into lag features for subsequent steps.
    """
    model = load_model(location_id)

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    last = df.iloc[-1]
    last_ts: pd.Timestamp = last["timestamp"]

    # Build a lookup of historical AQI by timestamp for lag resolution
    ts_series = df["timestamp"]
    aqi_series = df["aqi"].values

    predicted_aqis: list[float] = []

    def _lag_aqi(step: int, lag_hours: int) -> float:
        """Return AQI at (last_ts + step*1h - lag_hours*1h).

        step is 1-indexed (1 = first future hour).
        If the target time falls within predicted range, use the buffer;
        otherwise look up the nearest historical reading.
        """
        pred_step = step - lag_hours  # which predicted step we need (1-indexed)
        if pred_step >= 1:
            return predicted_aqis[pred_step - 1]
        # Historical lookup: find reading closest to the target timestamp
        target = last_ts + pd.Timedelta(hours=step - lag_hours)
        deltas = (ts_series - target).abs()
        return float(aqi_series[deltas.idxmin()])

    results: list[dict] = []
    for h in range(1, 25):
        future_ts = last_ts + pd.Timedelta(hours=h)

        features = {
            "pm25": float(last["pm25"]),
            "pm10": float(last["pm10"]),
            "co": float(last["co"]),
            "no2": float(last["no2"]),
            "so2": float(last["so2"]),
            "o3": float(last["o3"]),
            "aqi_lag_1h": _lag_aqi(h, 1),
            "aqi_lag_3h": _lag_aqi(h, 3),
            "aqi_lag_24h": _lag_aqi(h, 24),
            "hour": future_ts.hour,
            "day_of_week": future_ts.dayofweek,
            "month": future_ts.month,
            "is_weekend": int(future_ts.dayofweek >= 5),
        }

        X = pd.DataFrame([features])[FEATURE_COLS]
        predicted_aqi = float(max(0.0, model.predict(X)[0]))
        predicted_aqis.append(predicted_aqi)

        results.append(
            {
                "forecast_for": future_ts.to_pydatetime(),
                "predicted_aqi": round(predicted_aqi, 2),
            }
        )

    return results
