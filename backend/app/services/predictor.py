from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np

from app.ml.features import features_from_payload


class DroughtPredictor:
    def __init__(self, model_path: Path):
        self.model_path = model_path
        self.artifact = None

    def load(self) -> None:
        if self.model_path.exists():
            self.artifact = joblib.load(self.model_path)

    @property
    def ready(self) -> bool:
        return self.artifact is not None

    def predict(self, payload: dict[str, float | str]) -> dict[str, float | str]:
        features = features_from_payload(payload)
        if self.artifact is None:
            risk_score = self._fallback_score(payload)
        else:
            model = self.artifact["model"]
            risk_score = float(np.clip(model.predict(features)[0], 0, 100))
        severity = severity_from_score(risk_score)
        probability = round(float(risk_score / 100), 4)
        return {
            "severity": severity,
            "probability": probability,
            "risk_score": round(risk_score, 2),
            "recommendation": recommendation_for(severity),
            "suitable_crops": crops_for(severity, str(payload.get("state", ""))),
        }

    @staticmethod
    def _fallback_score(payload: dict[str, float | str]) -> float:
        ndvi = float(payload["ndvi"])
        lst = float(payload["lst"])
        rainfall = float(payload["rainfall"])
        soil = float(payload["soil_moisture_proxy"])
        score = 35 * max(0, 0.75 - ndvi) + 25 * max(0, 1 - rainfall / 220) + 20 * max(0, (lst - 28) / 18) + 20 * (1 - soil)
        return float(np.clip(score, 0, 100))


def severity_from_score(score: float) -> str:
    if score >= 75:
        return "Extreme Drought"
    if score >= 55:
        return "Severe Drought"
    if score >= 35:
        return "Moderate Drought"
    if score >= 20:
        return "Mild Drought"
    return "No Drought"


def recommendation_for(severity: str) -> str:
    recommendations = {
        "Extreme Drought": "Activate emergency irrigation scheduling, crop advisories, and local administration alerts.",
        "Severe Drought": "Prioritize water allocation, monitor crop stress weekly, and advise drought-tolerant practices.",
        "Moderate Drought": "Increase field monitoring and recommend supplemental irrigation where available.",
        "Mild Drought": "Watch rainfall trends and notify farmers about early moisture stress.",
        "No Drought": "Continue routine monitoring.",
    }
    return recommendations[severity]


def crops_for(severity: str, state: str) -> list[str]:
    dryland_crops = ["Millets", "Sorghum/Jowar", "Pearl millet/Bajra", "Pulses", "Sesame"]
    moderate_crops = ["Groundnut", "Cotton", "Pigeon pea/Tur", "Chickpea", "Sunflower"]
    normal_crops = ["Rice", "Maize", "Wheat", "Soybean", "Vegetables"]
    state_specific = {
        "Punjab": ["Wheat", "Maize", "Mustard"],
        "Haryana": ["Wheat", "Mustard", "Pearl millet/Bajra"],
        "Rajasthan": ["Pearl millet/Bajra", "Moth bean", "Cluster bean/Guar"],
        "Gujarat": ["Groundnut", "Cotton", "Castor"],
        "Maharashtra": ["Jowar", "Pigeon pea/Tur", "Cotton"],
        "Karnataka": ["Ragi", "Groundnut", "Pigeon pea/Tur"],
        "Tamil Nadu": ["Ragi", "Black gram", "Groundnut"],
        "Kerala": ["Coconut", "Tapioca", "Banana"],
        "West Bengal": ["Rice", "Jute", "Pulses"],
        "Assam": ["Rice", "Mustard", "Tea"],
    }
    if severity in {"Extreme Drought", "Severe Drought"}:
        base = dryland_crops
    elif severity == "Moderate Drought":
        base = moderate_crops
    elif severity == "Mild Drought":
        base = ["Maize", "Soybean", "Chickpea", "Mustard", "Vegetables with drip irrigation"]
    else:
        base = normal_crops
    merged = state_specific.get(state, []) + base
    return list(dict.fromkeys(merged))[:6]
