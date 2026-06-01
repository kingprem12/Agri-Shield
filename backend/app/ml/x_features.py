from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pywt
from sklearn.preprocessing import RobustScaler


X_FEATURES = [
    "ndvi",
    "lst",
    "rainfall",
    "temperature",
    "humidity",
    "solar_radiation",
    "wind_speed",
    "soil_moisture",
    "vci",
    "tci",
    "spi",
    "spei",
    "mndwi",
    "month_sin",
    "month_cos",
    "vhi_lag_1",
    "vhi_lag_3",
    "vhi_roll_3",
    "ndvi_wavelet_approx",
    "ndvi_wavelet_detail",
    "lst_wavelet_approx",
    "lst_wavelet_detail",
    "rainfall_wavelet_approx",
    "rainfall_wavelet_detail",
]


def read_custom_csvs(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = pd.read_csv(path)
        frame["source_file"] = path.name
        frames.append(frame)
    if not frames:
        raise ValueError("No CSV files supplied")
    return pd.concat(frames, ignore_index=True)


def parse_geo_column(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    if ".geo" not in data.columns:
        data["longitude"] = np.nan
        data["latitude"] = np.nan
        return data

    def parse(value: object) -> tuple[float, float]:
        try:
            geo = json.loads(str(value))
            coords = geo.get("coordinates", [])
            if isinstance(coords, list) and len(coords) >= 2:
                return float(coords[0]), float(coords[1])
        except Exception:
            pass
        return np.nan, np.nan

    coords = data[".geo"].apply(parse)
    data["longitude"] = coords.apply(lambda item: item[0])
    data["latitude"] = coords.apply(lambda item: item[1])
    return data


def standardize_remote_sensing_frame(frame: pd.DataFrame) -> pd.DataFrame:
    data = parse_geo_column(frame)
    rename_map = {
        "NDVI": "ndvi",
        "LST": "lst",
        "Precipitation": "rainfall",
        "precipitation": "rainfall",
        "SPEI_03_month": "spei",
        "Temperature": "temperature",
        "Humidity": "humidity",
        "Solar_Radiation": "solar_radiation",
        "Wind_Speed": "wind_speed",
        "Soil_Moisture": "soil_moisture",
    }
    data = data.rename(columns={key: value for key, value in rename_map.items() if key in data.columns})
    if "date" not in data.columns and {"year", "month"}.issubset(data.columns):
        data["date"] = data["year"].astype(str) + "-" + data["month"].astype(str).str.zfill(2)
    data["date"] = data["date"].astype(str).str.replace("_", "-", regex=False)
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    if data["date"].isna().any() and "source_file" in data.columns:
        extracted = data["source_file"].str.extract(r"(?P<year>20\d{2})[_-](?P<month>\d{2})")
        data.loc[data["date"].isna(), "date"] = pd.to_datetime(
            extracted["year"] + "-" + extracted["month"] + "-01", errors="coerce"
        )
    data["region"] = "Sindh"
    data["grid_id"] = data.get("system:index", pd.Series(np.arange(len(data)))).astype(str)
    for column in ["ndvi", "lst", "rainfall"]:
        if column not in data.columns:
            data[column] = np.nan
    data["rainfall"] = data["rainfall"].clip(lower=0)
    data["temperature"] = data.get("temperature", data["lst"] - 2)
    data["humidity"] = data.get("humidity", (65 - data["lst"] + data["rainfall"] / 8).clip(15, 95))
    data["solar_radiation"] = data.get("solar_radiation", (22 + data["lst"] * 0.35).clip(8, 35))
    data["wind_speed"] = data.get("wind_speed", (2.5 + data["lst"] / 30).clip(0.2, 8))
    data["soil_moisture"] = data.get("soil_moisture", (0.12 + data["rainfall"] / 300 + data["ndvi"] / 3).clip(0.02, 0.95))
    data["mndwi"] = data.get("mndwi", (data["rainfall"] / 250 - data["lst"] / 80).clip(-1, 1))
    return data


def clean_outliers(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    numeric = data.select_dtypes(include=["number"]).columns
    for column in numeric:
        q1, q3 = data[column].quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr > 0:
            data[column] = data[column].clip(q1 - 1.5 * iqr, q3 + 1.5 * iqr)
    data[numeric] = data[numeric].interpolate(limit_direction="both")
    data[numeric] = data[numeric].fillna(data[numeric].median())
    return data.ffill().bfill()


def _scaled_index(series: pd.Series, invert: bool = False) -> pd.Series:
    low = series.quantile(0.05)
    high = series.quantile(0.95)
    denom = max(high - low, 1e-6)
    value = ((series - low) / denom * 100).clip(0, 100)
    return 100 - value if invert else value


def _standardized(series: pd.Series) -> pd.Series:
    std = series.std()
    if not np.isfinite(std) or std == 0:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return ((series - series.mean()) / std).clip(-3, 3)


def _wavelet_pair(series: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    values = series.to_numpy(dtype=float)
    if len(values) < 4:
        return values, np.zeros_like(values)
    level = max(1, min(2, pywt.dwt_max_level(len(values), pywt.Wavelet("db4").dec_len)))
    coeffs = pywt.wavedec(values, "db4", mode="periodization", level=level)
    approx_coeffs = [coeffs[0]] + [np.zeros_like(coeff) for coeff in coeffs[1:]]
    detail_coeffs = [np.zeros_like(coeffs[0])] + coeffs[1:]
    approx = pywt.waverec(approx_coeffs, "db4", mode="periodization")[: len(values)]
    detail = pywt.waverec(detail_coeffs, "db4", mode="periodization")[: len(values)]
    return approx, detail


def engineer_research_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = standardize_remote_sensing_frame(frame)
    data = clean_outliers(data).sort_values(["grid_id", "date"])
    grouped = data.groupby("grid_id", group_keys=False)
    data["vci"] = grouped["ndvi"].transform(_scaled_index)
    data["tci"] = grouped["lst"].transform(lambda series: _scaled_index(series, invert=True))
    data["vhi"] = (0.5 * data["vci"] + 0.5 * data["tci"]).clip(0, 100)
    data["spi"] = grouped["rainfall"].transform(_standardized)
    if "spei" not in data.columns:
        water_balance = data["rainfall"] - (data["temperature"].clip(lower=0) * 2)
        data["spei"] = water_balance.groupby(data["grid_id"]).transform(_standardized)
    data["month"] = data["date"].dt.month
    data["month_sin"] = np.sin(2 * np.pi * data["month"] / 12)
    data["month_cos"] = np.cos(2 * np.pi * data["month"] / 12)
    data["vhi_lag_1"] = grouped["vhi"].shift(1)
    data["vhi_lag_3"] = grouped["vhi"].shift(3)
    data["vhi_roll_3"] = grouped["vhi"].transform(lambda series: series.rolling(3, min_periods=1).mean())
    for column in ["ndvi", "lst", "rainfall"]:
        pairs = grouped[column].transform(lambda series: pd.Series(_wavelet_pair(series)[0], index=series.index))
        details = grouped[column].transform(lambda series: pd.Series(_wavelet_pair(series)[1], index=series.index))
        data[f"{column}_wavelet_approx"] = pairs
        data[f"{column}_wavelet_detail"] = details
    data = clean_outliers(data)
    data["target_vhi_next"] = grouped["vhi"].shift(-1)
    data["target_vhi_next"] = data["target_vhi_next"].fillna(data["vhi"])
    return data


def scale_features(frame: pd.DataFrame) -> tuple[pd.DataFrame, RobustScaler]:
    scaler = RobustScaler()
    scaled = frame.copy()
    scaled[X_FEATURES] = scaler.fit_transform(frame[X_FEATURES])
    return scaled, scaler


def severity_from_vhi(vhi: float) -> str:
    if vhi < 20:
        return "Extreme Drought"
    if vhi < 35:
        return "Severe Drought"
    if vhi < 50:
        return "Moderate Drought"
    if vhi < 65:
        return "Mild Drought"
    return "No Drought"

