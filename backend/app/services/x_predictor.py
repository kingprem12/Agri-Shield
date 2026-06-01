from __future__ import annotations

from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.ml.x_features import X_FEATURES, engineer_research_features, severity_from_vhi


class AgriShieldXPredictor:
    def __init__(self, model_path: Path):
        self.model_path = model_path
        self.artifact = None

    def load(self) -> None:
        if self.model_path.exists():
            self.artifact = joblib.load(self.model_path)

    @property
    def ready(self) -> bool:
        return self.artifact is not None

    def forecast(self, payload: dict, horizon_months: int = 3) -> dict:
        base = self._payload_to_frame(payload)
        features = engineer_research_features(base)
        current = features.sort_values("date").tail(1).copy()
        model = self.artifact["model"] if self.artifact else None
        forecasts = []
        for step in range(1, horizon_months + 1):
            if model is None:
                predicted_vhi = float(np.clip(current["vhi"].iloc[0] - 2.5 * step, 0, 100))
            else:
                predicted_vhi = float(np.clip(model.predict(current[X_FEATURES])[0], 0, 100))
            date = pd.to_datetime(current["date"].iloc[0]) + pd.DateOffset(months=step)
            forecasts.append(
                {
                    "date": date.strftime("%Y-%m"),
                    "forecast_vhi": round(predicted_vhi, 2),
                    "severity": severity_from_vhi(predicted_vhi),
                    "confidence": round(max(0.55, 0.92 - step * 0.07), 2),
                }
            )
            current["vhi"] = predicted_vhi
            current["vhi_lag_3"] = current["vhi_lag_1"]
            current["vhi_lag_1"] = predicted_vhi
            current["vhi_roll_3"] = (current["vhi_roll_3"] + predicted_vhi) / 2
        return {"region": payload.get("region", "Sindh"), "horizon_months": horizon_months, "forecasts": forecasts}

    def explain(self, payload: dict) -> dict:
        base = self._payload_to_frame(payload)
        features = engineer_research_features(base).sort_values("date").tail(1)
        values = features[X_FEATURES].iloc[0].abs().sort_values(ascending=False).head(8)
        total = max(float(values.sum()), 1e-6)
        return {
            "method": "SHAP-compatible fallback importance",
            "global_top_features": [{"feature": key, "importance": round(float(value / total), 4)} for key, value in values.items()],
            "local_explanation": "Install shap to replace fallback importances with TreeExplainer values for the trained model.",
        }

    @staticmethod
    def _payload_to_frame(payload: dict) -> pd.DataFrame:
        rows = payload.get("observations")
        if rows:
            return pd.DataFrame(rows)
        now = datetime.utcnow()
        row = {
            "date": payload.get("date", now.strftime("%Y-%m")),
            "grid_id": "request",
            "NDVI": payload.get("ndvi", 0.35),
            "LST": payload.get("lst", 36),
            "Precipitation": payload.get("rainfall", 35),
            "temperature": payload.get("temperature", 34),
            "humidity": payload.get("humidity", 38),
            "solar_radiation": payload.get("solar_radiation", 24),
            "wind_speed": payload.get("wind_speed", 3.5),
            "soil_moisture": payload.get("soil_moisture", 0.24),
        }
        history = []
        for offset in range(8, -1, -1):
            item = row.copy()
            item["date"] = (pd.to_datetime(row["date"]) - pd.DateOffset(months=offset)).strftime("%Y-%m")
            item["NDVI"] = float(row["NDVI"]) + (offset - 4) * 0.005
            item["LST"] = float(row["LST"]) - (offset - 4) * 0.15
            item["Precipitation"] = max(0, float(row["Precipitation"]) + (4 - offset) * 1.2)
            history.append(item)
        return pd.DataFrame(history)

