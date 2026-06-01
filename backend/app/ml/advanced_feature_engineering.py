from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pywt


BASE_SIGNAL_COLUMNS = [
    "ndvi",
    "lst",
    "rainfall",
    "temperature",
    "humidity",
    "evapotranspiration",
    "soil_moisture",
    "vci",
    "tci",
    "vhi",
    "spi",
    "spei",
]

LAGS = [1, 2, 3, 6]
ROLLING_WINDOWS = [3, 6, 12]


def read_grid_csvs(csv_paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in sorted(csv_paths):
        frame = pd.read_csv(path)
        frame["source_file"] = path.name
        frames.append(frame)
    if not frames:
        raise ValueError("No real CSV files were supplied for benchmark training")
    return pd.concat(frames, ignore_index=True)


def build_advanced_drought_frame(csv_paths: list[Path], max_grid_rows: int | None = 120_000) -> pd.DataFrame:
    data = _standardize(read_grid_csvs(csv_paths))
    data = data.groupby(["grid_id", "date"], as_index=False).mean(numeric_only=True)
    data = data.sort_values(["grid_id", "date"]).reset_index(drop=True)
    data = _add_indices(data)
    data = _add_time_features(data)
    if max_grid_rows and len(data) > max_grid_rows:
        dates_per_grid = max(1, int(data.groupby("grid_id")["date"].nunique().median()))
        grid_count = max(8, int(max_grid_rows / dates_per_grid))
        selected_grids = (
            pd.Series(data["grid_id"].unique())
            .sample(min(grid_count, data["grid_id"].nunique()), random_state=42)
            .astype(str)
            .tolist()
        )
        data = data[data["grid_id"].astype(str).isin(selected_grids)].copy()
    data = _add_lag_roll_wavelet_features(data)
    grouped = data.groupby("grid_id", group_keys=False)
    for horizon in [1, 2, 3, 6]:
        data[f"target_vhi_h{horizon}"] = grouped["vhi"].shift(-horizon)
        data[f"target_severity_score_h{horizon}"] = (1.0 - data[f"target_vhi_h{horizon}"]).clip(0, 1)
    data["same_month_vhi"] = data["vhi"]
    data["severity_class"] = data["vhi"].apply(severity_class_from_vhi)
    required = feature_columns(data) + ["target_vhi_h1"]
    data = data.dropna(subset=required).reset_index(drop=True)
    if max_grid_rows and len(data) > max_grid_rows:
        data = data.sample(max_grid_rows, random_state=42).sort_values(["grid_id", "date"]).reset_index(drop=True)
    return data


def build_monthly_aggregate(grid_frame: pd.DataFrame) -> pd.DataFrame:
    numeric = grid_frame.select_dtypes(include=["number"]).columns
    monthly = grid_frame.groupby("date", as_index=False)[numeric].mean().sort_values("date")
    monthly["grid_id"] = "sindh_monthly"
    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly = _add_time_features(monthly)
    monthly = _add_lag_roll_wavelet_features(monthly)
    for horizon in [1, 2, 3, 6]:
        monthly[f"target_vhi_h{horizon}"] = monthly["vhi"].shift(-horizon)
        monthly[f"target_severity_score_h{horizon}"] = (1.0 - monthly[f"target_vhi_h{horizon}"]).clip(0, 1)
    monthly["same_month_vhi"] = monthly["vhi"]
    return monthly.dropna(subset=feature_columns(monthly) + ["target_vhi_h1"]).reset_index(drop=True)


def feature_columns(frame: pd.DataFrame) -> list[str]:
    excluded_prefixes = ("target_",)
    excluded = {"same_month_vhi", "severity_class", "year", "source_file"}
    columns = []
    for column in frame.columns:
        if column in {"date", "grid_id"} or column in excluded or column.startswith(excluded_prefixes):
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            columns.append(column)
    return columns


def drought_label(vhi: float) -> str:
    value = float(vhi)
    if value < 0.20:
        return "Extreme Drought"
    if value < 0.35:
        return "Severe Drought"
    if value < 0.50:
        return "Moderate Drought"
    if value < 0.65:
        return "Mild Drought"
    return "No Drought"


def severity_class_from_vhi(vhi: float) -> int:
    value = float(vhi)
    if value < 0.20:
        return 4
    if value < 0.35:
        return 3
    if value < 0.50:
        return 2
    if value < 0.65:
        return 1
    return 0


def _standardize(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    rename_map = {
        "system:index": "grid_id",
        "NDVI": "ndvi",
        "LST": "lst",
        "Precipitation": "rainfall",
        "Temperature": "temperature",
        "Humidity": "humidity",
        "Soil_Moisture": "soil_moisture",
        "Evapotranspiration": "evapotranspiration",
        "ET": "evapotranspiration",
        "SPEI_03_month": "spei",
    }
    data = data.rename(columns={key: value for key, value in rename_map.items() if key in data.columns})
    if "grid_id" not in data.columns:
        data["grid_id"] = np.arange(len(data)).astype(str)
    if "date" not in data.columns and {"year", "month"}.issubset(data.columns):
        data["date"] = data["year"].astype(str) + "-" + data["month"].astype(str).str.zfill(2)
    if "date" not in data.columns:
        extracted = data["source_file"].str.extract(r"(?P<year>20\d{2})[_-](?P<month>\d{2})")
        data["date"] = extracted["year"] + "-" + extracted["month"] + "-01"
    data["date"] = pd.to_datetime(data["date"].astype(str).str.replace("_", "-", regex=False), errors="coerce")
    if data["date"].isna().any():
        extracted = data["source_file"].str.extract(r"(?P<year>20\d{2})[_-](?P<month>\d{2})")
        data.loc[data["date"].isna(), "date"] = pd.to_datetime(
            extracted["year"] + "-" + extracted["month"] + "-01", errors="coerce"
        )
    if ".geo" in data.columns and ("longitude" not in data.columns or "latitude" not in data.columns):
        coords = data[".geo"].apply(_parse_geo)
        data["longitude"] = coords.apply(lambda item: item[0])
        data["latitude"] = coords.apply(lambda item: item[1])
    for column in ["ndvi", "lst", "rainfall"]:
        if column not in data.columns:
            data[column] = np.nan
    data["rainfall"] = data["rainfall"].clip(lower=0)
    data["temperature"] = data.get("temperature", data["lst"] - 2.0)
    data["humidity"] = data.get("humidity", (65 - data["lst"] + data["rainfall"] / 8).clip(15, 95))
    data["evapotranspiration"] = data.get(
        "evapotranspiration",
        (0.08 * data["temperature"].clip(lower=0) + 0.02 * (100 - data["humidity"]) + 0.01 * data["lst"]).clip(0, 12),
    )
    data["soil_moisture"] = data.get(
        "soil_moisture",
        (0.08 + data["rainfall"] / 350 + data["ndvi"].clip(0, 1) / 3 - data["evapotranspiration"] / 60).clip(0.02, 0.95),
    )
    numeric = data.select_dtypes(include=["number"]).columns
    data[numeric] = data[numeric].replace([np.inf, -np.inf], np.nan)
    data[numeric] = data[numeric].interpolate(limit_direction="both")
    data[numeric] = data[numeric].fillna(data[numeric].median(numeric_only=True))
    value_columns = [column for column in numeric if column not in {"grid_id", "date", "year", "month"}]
    return data[["grid_id", "date"] + value_columns].dropna(subset=["date"])


def _add_indices(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    grouped = data.groupby("grid_id", group_keys=False)
    data["vci"] = grouped["ndvi"].transform(lambda series: _scaled(series, invert=False))
    data["tci"] = grouped["lst"].transform(lambda series: _scaled(series, invert=True))
    data["vhi"] = (0.5 * data["vci"] + 0.5 * data["tci"]).clip(0, 1)
    data["spi"] = grouped["rainfall"].transform(_standardized)
    water_balance = data["rainfall"] - data["evapotranspiration"] * 20
    data["spei"] = water_balance.groupby(data["grid_id"]).transform(_standardized)
    return data


def _add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    data["month"] = data["date"].dt.month
    data["month_sin"] = np.sin(2 * np.pi * data["month"] / 12)
    data["month_cos"] = np.cos(2 * np.pi * data["month"] / 12)
    data["season"] = ((data["month"] % 12) // 3).astype(int)
    data["season_sin"] = np.sin(2 * np.pi * data["season"] / 4)
    data["season_cos"] = np.cos(2 * np.pi * data["season"] / 4)
    return data


def _add_lag_roll_wavelet_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.sort_values(["grid_id", "date"]).copy()
    grouped = data.groupby("grid_id", group_keys=False)
    for column in BASE_SIGNAL_COLUMNS:
        if column not in data.columns:
            continue
        for lag in LAGS:
            data[f"{column}_lag_{lag}"] = grouped[column].shift(lag)
        for window in ROLLING_WINDOWS:
            shifted = grouped[column].shift(1)
            data[f"{column}_roll_{window}"] = shifted.groupby(data["grid_id"]).transform(
                lambda series: series.rolling(window, min_periods=1).mean()
            )
        approx_detail = grouped[column].apply(_causal_wavelet_frame)
        data[f"{column}_wavelet_approx"] = approx_detail["approx"].to_numpy()
        data[f"{column}_wavelet_detail"] = approx_detail["detail"].to_numpy()
    numeric = data.select_dtypes(include=["number"]).columns
    data[numeric] = data[numeric].replace([np.inf, -np.inf], np.nan)
    data[numeric] = data.groupby("grid_id")[numeric].transform(lambda frame_part: frame_part.ffill().bfill())
    data[numeric] = data[numeric].fillna(data[numeric].median(numeric_only=True))
    return data


def _causal_wavelet_frame(series: pd.Series, window: int = 12) -> pd.DataFrame:
    shifted = series.shift(1).ffill().bfill()
    approx_values = []
    detail_values = []
    for position in range(len(shifted)):
        history = shifted.iloc[max(0, position - window + 1) : position + 1].to_numpy(dtype=float)
        if len(history) < 4 or np.nanstd(history) == 0:
            approx_values.append(float(history[-1]) if len(history) else 0.0)
            detail_values.append(0.0)
            continue
        level = max(1, min(2, pywt.dwt_max_level(len(history), pywt.Wavelet("db4").dec_len)))
        coeffs = pywt.wavedec(history, "db4", mode="periodization", level=level)
        approx_coeffs = [coeffs[0]] + [np.zeros_like(coeff) for coeff in coeffs[1:]]
        detail_coeffs = [np.zeros_like(coeffs[0])] + coeffs[1:]
        approx = pywt.waverec(approx_coeffs, "db4", mode="periodization")[: len(history)]
        detail = pywt.waverec(detail_coeffs, "db4", mode="periodization")[: len(history)]
        approx_values.append(float(approx[-1]))
        detail_values.append(float(detail[-1]))
    return pd.DataFrame({"approx": approx_values, "detail": detail_values}, index=series.index)


def _scaled(series: pd.Series, invert: bool) -> pd.Series:
    low, high = series.quantile([0.05, 0.95])
    scaled = ((series - low) / max(high - low, 1e-6)).clip(0, 1)
    return 1 - scaled if invert else scaled


def _standardized(series: pd.Series) -> pd.Series:
    std = series.std()
    if not np.isfinite(std) or std == 0:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return ((series - series.mean()) / std).clip(-3, 3)


def _parse_geo(value: object) -> tuple[float, float]:
    try:
        geo = json.loads(str(value))
        coords = geo.get("coordinates", [])
        return float(coords[0]), float(coords[1])
    except Exception:
        return np.nan, np.nan
