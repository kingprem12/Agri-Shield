from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from app.ml.features import MODEL_FEATURES, prepare_training_frame


def _models() -> dict[str, object]:
    return {
        "linear_regression": Pipeline([("scale", StandardScaler()), ("model", LinearRegression())]),
        "random_forest": RandomForestRegressor(n_estimators=120, max_depth=8, random_state=42),
        "xgboost": XGBRegressor(
            n_estimators=160,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="reg:squarederror",
            random_state=42,
        ),
    }


def evaluate_models(frame: pd.DataFrame) -> tuple[str, object, list[dict[str, float | str]]]:
    data = frame.sort_values("date")
    x = data[MODEL_FEATURES]
    y = data["risk_score"]
    splits = min(5, max(2, len(data) // 18))
    tscv = TimeSeriesSplit(n_splits=splits)
    results: list[dict[str, float | str]] = []
    best_name = ""
    best_rmse = float("inf")
    best_model: object | None = None

    for name, model in _models().items():
        rmses: list[float] = []
        r2s: list[float] = []
        for train_idx, test_idx in tscv.split(x):
            model.fit(x.iloc[train_idx], y.iloc[train_idx])
            preds = np.clip(model.predict(x.iloc[test_idx]), 0, 100)
            rmses.append(float(mean_squared_error(y.iloc[test_idx], preds) ** 0.5))
            r2s.append(float(r2_score(y.iloc[test_idx], preds)))
        mean_rmse = float(np.mean(rmses))
        result = {"model": name, "rmse": mean_rmse, "r2": float(np.mean(r2s))}
        results.append(result)
        if mean_rmse < best_rmse:
            best_rmse = mean_rmse
            best_name = name
            best_model = model

    assert best_model is not None
    best_model.fit(x, y)
    return best_name, best_model, results


def train_from_csv(input_csv: Path, model_path: Path, report_path: Path) -> dict[str, object]:
    raw = pd.read_csv(input_csv)
    training_frame = prepare_training_frame(raw)
    best_name, best_model, results = evaluate_models(training_frame)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    artifact = {"model_name": best_name, "model": best_model, "features": MODEL_FEATURES}
    joblib.dump(artifact, model_path)
    report = {"best_model": best_name, "metrics": results, "rows": len(training_frame)}
    report_path.write_text(json.dumps(report, indent=2))
    return report

