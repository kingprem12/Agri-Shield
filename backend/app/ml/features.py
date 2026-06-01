from __future__ import annotations

import numpy as np
import pandas as pd
import pywt


BASE_FEATURES = [
    "ndvi",
    "lst",
    "rainfall",
    "temperature",
    "humidity",
    "wind_speed",
    "soil_moisture_proxy",
]


MODEL_FEATURES = BASE_FEATURES + [
    "ndvi_lag_1",
    "rainfall_lag_1",
    "lst_lag_1",
    "ndvi_roll_3",
    "rainfall_roll_3",
    "lst_roll_3",
    "ndvi_wavelet_low",
    "rainfall_wavelet_low",
    "lst_wavelet_low",
]


def clean_missing_values(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy()
    numeric_columns = cleaned.select_dtypes(include=["number"]).columns
    cleaned[numeric_columns] = cleaned[numeric_columns].interpolate(limit_direction="both")
    cleaned[numeric_columns] = cleaned[numeric_columns].fillna(cleaned[numeric_columns].median())
    cleaned = cleaned.ffill().bfill()
    return cleaned


def monthly_aggregate(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    data["date"] = pd.to_datetime(data["date"])
    group_cols = ["state", "district", pd.Grouper(key="date", freq="MS")]
    aggregated = data.groupby(group_cols, as_index=False)[BASE_FEATURES].mean()
    return aggregated.sort_values(["state", "district", "date"]).reset_index(drop=True)


def _wavelet_low_frequency(values: pd.Series, wavelet: str = "db4") -> np.ndarray:
    arr = values.to_numpy(dtype=float)
    if len(arr) < 4:
        return arr
    max_level = pywt.dwt_max_level(len(arr), pywt.Wavelet(wavelet).dec_len)
    level = max(1, min(2, max_level))
    coeffs = pywt.wavedec(arr, wavelet, mode="periodization", level=level)
    coeffs[1:] = [np.zeros_like(coeff) for coeff in coeffs[1:]]
    reconstructed = pywt.waverec(coeffs, wavelet, mode="periodization")
    return reconstructed[: len(arr)]


def add_temporal_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy().sort_values(["state", "district", "date"])
    grouped = data.groupby(["state", "district"], group_keys=False)
    for column in ["ndvi", "rainfall", "lst"]:
        data[f"{column}_lag_1"] = grouped[column].shift(1)
        data[f"{column}_roll_3"] = grouped[column].transform(lambda series: series.rolling(3, min_periods=1).mean())
        data[f"{column}_wavelet_low"] = grouped[column].transform(_wavelet_low_frequency)
    return clean_missing_values(data)


def drought_risk_target(frame: pd.DataFrame) -> pd.Series:
    ndvi_stress = (0.75 - frame["ndvi"]).clip(0, 1)
    heat_stress = ((frame["lst"] - 28) / 18).clip(0, 1)
    rainfall_deficit = (1 - (frame["rainfall"] / 220)).clip(0, 1)
    soil_stress = (1 - frame["soil_moisture_proxy"]).clip(0, 1)
    risk = 0.35 * ndvi_stress + 0.25 * rainfall_deficit + 0.2 * heat_stress + 0.2 * soil_stress
    return (risk * 100).clip(0, 100)


def prepare_training_frame(raw_frame: pd.DataFrame) -> pd.DataFrame:
    monthly = monthly_aggregate(clean_missing_values(raw_frame))
    engineered = add_temporal_features(monthly)
    engineered["risk_score"] = drought_risk_target(engineered)
    return engineered


def features_from_payload(payload: dict[str, float | str]) -> pd.DataFrame:
    row = {feature: float(payload[feature]) for feature in BASE_FEATURES}
    row.update(
        {
            "ndvi_lag_1": row["ndvi"],
            "rainfall_lag_1": row["rainfall"],
            "lst_lag_1": row["lst"],
            "ndvi_roll_3": row["ndvi"],
            "rainfall_roll_3": row["rainfall"],
            "lst_roll_3": row["lst"],
            "ndvi_wavelet_low": row["ndvi"],
            "rainfall_wavelet_low": row["rainfall"],
            "lst_wavelet_low": row["lst"],
        }
    )
    return pd.DataFrame([row], columns=MODEL_FEATURES)

