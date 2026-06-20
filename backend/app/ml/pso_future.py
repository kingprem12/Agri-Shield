from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pywt
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import f1_score, mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

from app.ml.advanced_feature_engineering import build_advanced_drought_frame, severity_class_from_vhi, _causal_wavelet_frame


BASE_PAPER = {"model": "Base paper Wavelet-XGBoost", "r2": 0.964, "rmse": 0.021, "mae": 0.023}
DEFAULT_DATASET_DIR = Path("/Users/prem/Documents/My Final year Project/Data Sets")
MODEL_PATH = Path("models/pso_future/pso_wavelet_lag_ensemble.joblib")
REPORT_PATH = Path("reports/pso_future_forecasting_metrics.json")
ACTUAL_VS_PREDICTED_PATH = Path("reports/pso_future_actual_vs_predicted.png")
METRIC_COMPARISON_PATH = Path("reports/pso_future_metric_comparison.png")

RAW_SIGNALS = [
    "ndvi",
    "lst",
    "rainfall",
    "temperature",
    "humidity",
    "evapotranspiration",
    "wind_speed",
    "solar_radiation",
    "evi",
    "modis_ndvi",
    "modis_lst",
    "chirps_rainfall",
    "rainfall_anomaly",
    "spi_1",
    "spi_3",
    "spi_6",
    "spi_12",
    "spei_1",
    "spei_3",
    "spei_6",
    "spei_12",
]
ROLLING_SIGNALS = ["ndvi", "lst", "rainfall", "vhi", "vci", "tci", "spi", "spei"]
SEASONAL = ["month_sin", "month_cos", "season_sin", "season_cos"]
SPATIAL = ["latitude", "longitude"]


@dataclass
class FuturePsoResult:
    params: dict
    selected_groups: list[str]
    sequence_length: int
    ensemble_weight: float
    validation_rmse: float
    history: list[dict]


def train_pso_future_forecaster(
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    pattern: str = "Sindh_Grid_*.csv",
    limit_files: int = 276,
    max_grid_rows: int = 30_000,
    particles: int = 5,
    iterations: int = 4,
    seed: int = 29,
    dataset_csv: Path | None = None,
    model_path: Path = MODEL_PATH,
    report_path: Path = REPORT_PATH,
) -> dict:
    csv_paths = [] if dataset_csv else sorted(dataset_dir.glob(pattern))[:limit_files]

    model_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    if dataset_csv:
        frame = build_enriched_future_frame(dataset_csv, max_grid_rows=max_grid_rows)
    else:
        if len(csv_paths) < 24:
            raise ValueError(f"Need at least 24 Sindh CSV files, found {len(csv_paths)}")
        frame = build_advanced_drought_frame(csv_paths, max_grid_rows=max_grid_rows)
    frame = _add_past_only_rolling_std(frame)
    train, test, spatial_train, spatial_test = _strict_splits(frame)
    train_fit, valid = _chronological_validation_split(train)

    result = _pso_search(train_fit, valid, particles=particles, iterations=iterations, seed=seed)

    x_train, y_train, features = _supervised_matrix(train, result.sequence_length, result.selected_groups)
    x_test, y_test, _ = _supervised_matrix(test, result.sequence_length, result.selected_groups, feature_names=features)
    et, xgb = _fit_models(x_train, y_train, result.params, seed=seed)
    pred = _ensemble_predict(et, xgb, x_test, result.ensemble_weight)
    strict_metrics = _forecast_metrics(y_test, pred)
    beat = {
        "r2": strict_metrics["r2"] > BASE_PAPER["r2"],
        "rmse": strict_metrics["rmse"] < BASE_PAPER["rmse"],
        "mae": strict_metrics["mae"] < BASE_PAPER["mae"],
    }

    artifact = {
        "extra_trees": et,
        "xgboost": xgb,
        "ensemble_weight_extra_trees": result.ensemble_weight,
        "features": features,
        "selected_groups": result.selected_groups,
        "sequence_length": result.sequence_length,
        "params": result.params,
        "protocol": "strict_next_month_forecasting",
        "leakage_guard": "Features end at month t; target is VHI at t+1. Target-month VHI/VCI/TCI are not used.",
    }
    joblib.dump(artifact, model_path)
    plots = _save_plots(y_test, pred, strict_metrics, report_path.parent)

    x_sp_train, y_sp_train, _ = _supervised_matrix(spatial_train, result.sequence_length, result.selected_groups, feature_names=features)
    x_sp_test, y_sp_test, _ = _supervised_matrix(spatial_test, result.sequence_length, result.selected_groups, feature_names=features)
    x_sp_train, y_sp_train = _sample_xy(x_sp_train, y_sp_train, max_rows=12_000, seed=seed)
    x_sp_test, y_sp_test = _sample_xy(x_sp_test, y_sp_test, max_rows=10_000, seed=seed + 1)
    sp_et, sp_xgb = _fit_models(x_sp_train, y_sp_train, result.params, seed=seed)
    sp_pred = _ensemble_predict(sp_et, sp_xgb, x_sp_test, result.ensemble_weight)

    rolling = _rolling_origin_validation(frame, result, features, seed=seed)
    spatial_metrics = _forecast_metrics(y_sp_test, sp_pred)
    report = {
        "project": "AgriShield-X",
        "model": "PSO-Optimized Wavelet-Lag ExtraTrees + XGBoost Ensemble",
        "base_paper": BASE_PAPER,
        "dataset": _dataset_summary(frame, csv_paths),
        "pso": {
            "particles": particles,
            "iterations": iterations,
            "seed": seed,
            "best_params": result.params,
            "selected_feature_groups": result.selected_groups,
            "sequence_length": result.sequence_length,
            "ensemble_weight_extra_trees": result.ensemble_weight,
            "ensemble_weight_xgboost": 1 - result.ensemble_weight,
            "validation_rmse": result.validation_rmse,
            "history": result.history,
        },
        "protocols": {
            "A_strict_chronological_next_month_forecasting": {
                "model": "PSO Wavelet-Lag ExtraTrees + XGBoost Ensemble",
                "protocol": "A_strict_chronological_next_month_forecasting",
                **strict_metrics,
            },
            "D_spatial_holdout_secondary": {
                "model": "PSO Wavelet-Lag ExtraTrees + XGBoost Ensemble",
                "protocol": "D_spatial_holdout_secondary",
                **spatial_metrics,
            },
            "E_rolling_origin_validation": rolling,
        },
        "actual_vs_predicted_sample": _prediction_sample(y_test, pred),
        "success_against_base_paper_strict": beat,
        "beat_paper_strict": any(beat.values()),
        "claim": _claim(strict_metrics, beat),
        "honesty_note": "This report uses true next-month forecasting only. Same-month estimation and random split metrics are intentionally excluded as main results.",
        "artifact_path": str(model_path),
        "plots": plots,
    }
    report_path.write_text(json.dumps(_json_ready(report), indent=2))
    return report


def build_enriched_future_frame(dataset_csv: Path, max_grid_rows: int | None = 30_000) -> pd.DataFrame:
    data = pd.read_csv(dataset_csv, parse_dates=["date"])
    data["grid_id"] = data["grid_id"].astype(str)
    if "rainfall" not in data.columns:
        data["rainfall"] = data["chirps_rainfall"] if "chirps_rainfall" in data.columns else data.get("precipitation", 0.0)
    if "spi" not in data.columns and "spi_3" in data.columns:
        data["spi"] = data["spi_3"]
    if "spei" not in data.columns and "spei_3" in data.columns:
        data["spei"] = data["spei_3"]
    required = ["grid_id", "date", "vhi", "vhi_next_month"]
    missing_required = [column for column in required if column not in data.columns]
    if missing_required:
        raise ValueError(f"Enriched dataset is missing required columns: {missing_required}")
    data = data.groupby(["grid_id", "date"], as_index=False).mean(numeric_only=True)
    data = data.sort_values(["grid_id", "date"]).reset_index(drop=True)
    data = _add_time_features_local(data)
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
    data = _add_lag_roll_wavelet_features_local(data)
    data["target_vhi_h1"] = data["vhi_next_month"]
    data["same_month_vhi"] = data["vhi"]
    data["severity_class"] = data["vhi"].apply(severity_class_from_vhi)
    numeric = data.select_dtypes(include=["number"]).columns
    data[numeric] = data[numeric].replace([np.inf, -np.inf], np.nan)
    data[numeric] = data.groupby("grid_id")[numeric].transform(lambda item: item.ffill().bfill())
    data[numeric] = data[numeric].fillna(data[numeric].median(numeric_only=True))
    required_features = _base_features(data, ["raw", "lag", "rolling_mean", "rolling_std", "seasonal", "wavelet", "spatial"])
    data = data.dropna(subset=required_features + ["target_vhi_h1"]).reset_index(drop=True)
    if max_grid_rows and len(data) > max_grid_rows:
        data = data.sample(max_grid_rows, random_state=42).sort_values(["grid_id", "date"]).reset_index(drop=True)
    return data


def _add_time_features_local(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    data["month"] = data["date"].dt.month
    data["month_sin"] = np.sin(2 * np.pi * data["month"] / 12)
    data["month_cos"] = np.cos(2 * np.pi * data["month"] / 12)
    data["season"] = ((data["month"] % 12) // 3).astype(int)
    data["season_sin"] = np.sin(2 * np.pi * data["season"] / 4)
    data["season_cos"] = np.cos(2 * np.pi * data["season"] / 4)
    return data


def _add_lag_roll_wavelet_features_local(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.sort_values(["grid_id", "date"]).copy()
    grouped = data.groupby("grid_id", group_keys=False)
    signals = [column for column in sorted(set(RAW_SIGNALS + ROLLING_SIGNALS + ["soil_moisture", "mndwi"])) if column in data.columns]
    for column in signals:
        for lag in [1, 2, 3, 6, 12]:
            data[f"{column}_lag_{lag}"] = grouped[column].shift(lag)
        shifted = grouped[column].shift(1)
        for window in [3, 6, 12]:
            data[f"{column}_roll_{window}"] = shifted.groupby(data["grid_id"]).transform(
                lambda series: series.rolling(window, min_periods=1).mean()
            )
        approx_detail = grouped[column].apply(_causal_wavelet_frame)
        data[f"{column}_wavelet_approx"] = approx_detail["approx"].to_numpy()
        data[f"{column}_wavelet_detail"] = approx_detail["detail"].to_numpy()
    return data


def load_future_report(report_path: Path = REPORT_PATH) -> dict:
    if not report_path.exists():
        return {"status": "missing", "message": "PSO future forecaster has not been trained yet."}
    return json.loads(report_path.read_text())


def load_future_artifact(model_path: Path = MODEL_PATH) -> dict | None:
    if not model_path.exists():
        return None
    return joblib.load(model_path)


def predict_future_from_payload(payload: dict, artifact: dict) -> dict:
    values = {feature: float(payload.get(feature.split("__")[0], payload.get(feature, 0.0))) for feature in artifact["features"]}
    x = np.array([[values[feature] for feature in artifact["features"]]], dtype=float)
    if "model" in artifact:
        pred = np.clip(artifact["model"].predict(x), 0, 1)
    else:
        pred = _ensemble_predict(artifact["extra_trees"], artifact["xgboost"], x, artifact["ensemble_weight_extra_trees"])
    vhi = float(np.clip(pred[0], 0, 1))
    return {
        "predicted_next_month_vhi": vhi,
        "drought_severity": _severity_label(vhi),
        "risk_score": float((1 - vhi) * 100),
        "protocol": "strict_next_month_forecasting",
    }


def _pso_search(train: pd.DataFrame, valid: pd.DataFrame, particles: int, iterations: int, seed: int) -> FuturePsoResult:
    rng = np.random.default_rng(seed)
    dimensions = 21
    positions = rng.random((particles, dimensions))
    velocities = rng.normal(0, 0.08, size=(particles, dimensions))
    personal_best = positions.copy()
    personal_scores = np.full(particles, np.inf)
    global_best = positions[0].copy()
    global_score = np.inf
    history = []

    for iteration in range(iterations):
        inertia = 0.72 - 0.22 * (iteration / max(iterations - 1, 1))
        c1 = 1.35
        c2 = 1.65
        for particle in range(particles):
            decoded = _decode_particle(positions[particle])
            score = _validation_score(train, valid, decoded, seed + particle)
            history.append(
                {
                    "iteration": iteration,
                    "particle": particle,
                    "rmse": score,
                    "sequence_length": decoded.sequence_length,
                    "selected_groups": decoded.selected_groups,
                    "ensemble_weight_extra_trees": decoded.ensemble_weight,
                    "params": decoded.params,
                }
            )
            if score < personal_scores[particle]:
                personal_scores[particle] = score
                personal_best[particle] = positions[particle].copy()
            if score < global_score:
                global_score = score
                global_best = positions[particle].copy()
        r1 = rng.random((particles, dimensions))
        r2 = rng.random((particles, dimensions))
        velocities = inertia * velocities + c1 * r1 * (personal_best - positions) + c2 * r2 * (global_best - positions)
        positions = np.clip(positions + velocities, 0, 1)
    best = _decode_particle(global_best)
    best.validation_rmse = float(global_score)
    best.history = history
    return best


def _decode_particle(particle: np.ndarray) -> FuturePsoResult:
    seq_choices = [3, 6, 12]
    groups = ["raw", "lag", "rolling_mean", "rolling_std", "seasonal", "wavelet", "spatial"]
    selected = [group for group, bit in zip(groups, particle[14:21]) if bit >= 0.38]
    if "raw" not in selected:
        selected.insert(0, "raw")
    params = {
        "et_n_estimators": int(80 + particle[0] * 120),
        "et_max_depth": int(8 + particle[1] * 18),
        "et_min_samples_leaf": int(1 + particle[2] * 4),
        "et_max_features": float(0.45 + particle[3] * 0.55),
        "xgb_max_depth": int(2 + particle[4] * 5),
        "xgb_learning_rate": float(0.012 + particle[5] * 0.075),
        "xgb_n_estimators": int(80 + particle[6] * 160),
        "xgb_subsample": float(0.60 + particle[7] * 0.38),
        "xgb_colsample_bytree": float(0.60 + particle[8] * 0.38),
        "xgb_reg_lambda": float(0.1 + particle[9] * 8),
        "xgb_reg_alpha": float(particle[10] * 3),
    }
    return FuturePsoResult(
        params=params,
        selected_groups=selected,
        sequence_length=seq_choices[min(int(particle[11] * len(seq_choices)), len(seq_choices) - 1)],
        ensemble_weight=float(0.15 + particle[12] * 0.75),
        validation_rmse=np.inf,
        history=[],
    )


def _validation_score(train: pd.DataFrame, valid: pd.DataFrame, decoded: FuturePsoResult, seed: int) -> float:
    try:
        x_train, y_train, features = _supervised_matrix(train, decoded.sequence_length, decoded.selected_groups)
        x_valid, y_valid, _ = _supervised_matrix(valid, decoded.sequence_length, decoded.selected_groups, feature_names=features)
        if len(x_train) < 100 or len(x_valid) < 30:
            return np.inf
        et, xgb = _fit_models(x_train, y_train, decoded.params, seed)
        pred = _ensemble_predict(et, xgb, x_valid, decoded.ensemble_weight)
        return math.sqrt(mean_squared_error(y_valid, pred))
    except Exception:
        return np.inf


def _fit_models(x: np.ndarray, y: np.ndarray, params: dict, seed: int):
    et = ExtraTreesRegressor(
        n_estimators=params["et_n_estimators"],
        max_depth=params["et_max_depth"],
        min_samples_leaf=params["et_min_samples_leaf"],
        max_features=params["et_max_features"],
        random_state=seed,
        n_jobs=-1,
    )
    xgb = XGBRegressor(
        n_estimators=params["xgb_n_estimators"],
        max_depth=params["xgb_max_depth"],
        learning_rate=params["xgb_learning_rate"],
        subsample=params["xgb_subsample"],
        colsample_bytree=params["xgb_colsample_bytree"],
        reg_lambda=params["xgb_reg_lambda"],
        reg_alpha=params["xgb_reg_alpha"],
        objective="reg:squarederror",
        tree_method="hist",
        random_state=seed,
        n_jobs=1,
    )
    et.fit(x, y)
    xgb.fit(x, y)
    return et, xgb


def _ensemble_predict(et, xgb, x: np.ndarray, weight: float) -> np.ndarray:
    return np.clip(weight * et.predict(x) + (1 - weight) * xgb.predict(x), 0, 1)


def _supervised_matrix(
    frame: pd.DataFrame,
    sequence_length: int,
    selected_groups: list[str],
    feature_names: list[str] | None = None,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    base_features = _base_features(frame, selected_groups)
    if feature_names is None:
        feature_names = [f"{feature}__t-{offset}" for offset in range(sequence_length - 1, -1, -1) for feature in base_features]
    rows = []
    targets = []
    for _, group in frame.sort_values(["grid_id", "date"]).groupby("grid_id", sort=False):
        group = group.sort_values("date")
        values = group[base_features].to_numpy(dtype=float)
        target = group["target_vhi_h1"].to_numpy(dtype=float)
        for index in range(sequence_length - 1, len(group)):
            rows.append(values[index - sequence_length + 1 : index + 1].reshape(-1))
            targets.append(target[index])
    x = np.asarray(rows, dtype=float)
    y = np.asarray(targets, dtype=float)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    return x, y, feature_names


def _base_features(frame: pd.DataFrame, groups: list[str]) -> list[str]:
    features: list[str] = []
    if "raw" in groups:
        features.extend([column for column in RAW_SIGNALS if column in frame.columns])
    if "lag" in groups:
        features.extend([column for column in frame.columns if any(column.endswith(f"_lag_{lag}") for lag in [1, 2, 3, 6, 12])])
    if "rolling_mean" in groups:
        features.extend([column for column in frame.columns if "_roll_" in column])
    if "rolling_std" in groups:
        features.extend([column for column in frame.columns if "_std_" in column])
    if "seasonal" in groups:
        features.extend([column for column in SEASONAL if column in frame.columns])
    if "wavelet" in groups:
        features.extend([column for column in frame.columns if "wavelet" in column])
    if "spatial" in groups:
        features.extend([column for column in SPATIAL if column in frame.columns])
    blocked = {"target_vhi_h1", "same_month_vhi", "severity_class", "vhi_next_month", "vhi", "vci", "tci"}
    return sorted(dict.fromkeys(column for column in features if column not in blocked and pd.api.types.is_numeric_dtype(frame[column])))


def _add_past_only_rolling_std(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.sort_values(["grid_id", "date"]).copy()
    grouped = data.groupby("grid_id", group_keys=False)
    for column in ROLLING_SIGNALS:
        if column not in data.columns:
            continue
        shifted = grouped[column].shift(1)
        for window in [3, 6, 12]:
            data[f"{column}_std_{window}"] = shifted.groupby(data["grid_id"]).transform(lambda item: item.rolling(window, min_periods=2).std())
    numeric = data.select_dtypes(include=["number"]).columns
    data[numeric] = data.groupby("grid_id")[numeric].transform(lambda item: item.ffill().bfill())
    data[numeric] = data[numeric].fillna(data[numeric].median(numeric_only=True))
    return data


def _strict_splits(frame: pd.DataFrame):
    split_cut = frame["date"].quantile(0.8)
    train = frame[frame["date"] <= split_cut].copy()
    test = frame[frame["date"] > split_cut].copy()
    grid_ids = np.array(sorted(frame["grid_id"].astype(str).unique()))
    rng = np.random.default_rng(41)
    holdout = set(rng.choice(grid_ids, size=max(1, int(len(grid_ids) * 0.2)), replace=False))
    spatial_train = frame[~frame["grid_id"].astype(str).isin(holdout)].copy()
    spatial_test = frame[frame["grid_id"].astype(str).isin(holdout)].copy()
    return train, test, spatial_train, spatial_test


def _chronological_validation_split(train: pd.DataFrame):
    cut = train["date"].quantile(0.85)
    return train[train["date"] <= cut].copy(), train[train["date"] > cut].copy()


def _rolling_origin_validation(frame: pd.DataFrame, result: FuturePsoResult, features: list[str], seed: int) -> dict:
    dates = sorted(frame["date"].unique())
    origins = [dates[int(len(dates) * fraction)] for fraction in [0.55, 0.65, 0.75]]
    metrics = []
    for origin in origins:
        train = frame[frame["date"] <= origin].copy()
        test_dates = [date for date in dates if date > origin][:12]
        test = frame[frame["date"].isin(test_dates)].copy()
        if test.empty:
            continue
        x_train, y_train, _ = _supervised_matrix(train, result.sequence_length, result.selected_groups, feature_names=features)
        x_test, y_test, _ = _supervised_matrix(test, result.sequence_length, result.selected_groups, feature_names=features)
        x_train, y_train = _sample_xy(x_train, y_train, max_rows=12_000, seed=seed)
        x_test, y_test = _sample_xy(x_test, y_test, max_rows=10_000, seed=seed + 1)
        et, xgb = _fit_models(x_train, y_train, result.params, seed)
        pred = _ensemble_predict(et, xgb, x_test, result.ensemble_weight)
        metrics.append(_forecast_metrics(y_test, pred))
    if not metrics:
        return {"protocol": "E_rolling_origin_validation", "folds": 0}
    averaged = {key: float(np.mean([row[key] for row in metrics])) for key in metrics[0]}
    return {"model": "PSO Wavelet-Lag Ensemble rolling-origin average", "protocol": "E_rolling_origin_validation", "folds": len(metrics), **averaged}


def _sample_xy(x: np.ndarray, y: np.ndarray, max_rows: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    if len(x) <= max_rows:
        return x, y
    rng = np.random.default_rng(seed)
    indices = np.sort(rng.choice(len(x), size=max_rows, replace=False))
    return x[indices], y[indices]


def _forecast_metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    rmse = math.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    denominator = np.maximum(np.abs(y_true), 1e-3)
    true_class = [severity_class_from_vhi(value) for value in y_true]
    pred_class = [severity_class_from_vhi(value) for value in y_pred]
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "rmse": float(rmse),
        "mae": float(mae),
        "mape": float(np.mean(np.abs((y_true - y_pred) / denominator))),
        "drought_severity_f1": float(f1_score(true_class, pred_class, average="weighted", zero_division=0)),
    }


def _save_plots(y_true, y_pred, strict_metrics: dict, report_dir: Path) -> dict:
    from PIL import Image, ImageDraw

    actual_path = report_dir / ACTUAL_VS_PREDICTED_PATH.name
    metric_path = report_dir / METRIC_COMPARISON_PATH.name

    width, height = 900, 360
    margin = 42
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((margin, margin, width - margin, height - margin), outline=(203, 213, 225))
    count = min(180, len(y_true))
    actual = np.asarray(y_true, dtype=float)[:count]
    predicted = np.asarray(y_pred, dtype=float)[:count]
    _draw_line(draw, actual, width, height, margin, fill=(5, 150, 105))
    _draw_line(draw, predicted, width, height, margin, fill=(37, 99, 235))
    draw.text((margin, 12), "Strict Future Forecasting: actual vs predicted", fill=(15, 23, 42))
    draw.text((margin, height - 28), "green=actual  blue=predicted", fill=(71, 85, 105))
    image.save(actual_path)

    image = Image.new("RGB", (720, 360), "white")
    draw = ImageDraw.Draw(image)
    labels = ["R2", "RMSE", "MAE"]
    ours = [strict_metrics["r2"], strict_metrics["rmse"], strict_metrics["mae"]]
    paper = [BASE_PAPER["r2"], BASE_PAPER["rmse"], BASE_PAPER["mae"]]
    max_value = max(max(ours), max(paper), 1e-6)
    draw.text((30, 16), "Strict Forecast vs Base Paper", fill=(15, 23, 42))
    for index, label in enumerate(labels):
        x = 80 + index * 200
        paper_height = int((paper[index] / max_value) * 240)
        ours_height = int((ours[index] / max_value) * 240)
        draw.rectangle((x, 300 - paper_height, x + 54, 300), fill=(148, 163, 184))
        draw.rectangle((x + 64, 300 - ours_height, x + 118, 300), fill=(37, 99, 235))
        draw.text((x, 314), label, fill=(15, 23, 42))
    draw.text((30, 330), "gray=base paper  blue=strict forecast", fill=(71, 85, 105))
    image.save(metric_path)
    return {"actual_vs_predicted": str(actual_path), "metric_comparison": str(metric_path)}


def _draw_line(draw, values: np.ndarray, width: int, height: int, margin: int, fill: tuple[int, int, int]) -> None:
    if len(values) < 2:
        return
    points = []
    for index, value in enumerate(values):
        x = margin + (index / max(len(values) - 1, 1)) * (width - 2 * margin)
        y = height - margin - float(np.clip(value, 0, 1)) * (height - 2 * margin)
        points.append((x, y))
    draw.line(points, fill=fill, width=2)


def _prediction_sample(y_true, y_pred, limit: int = 80) -> list[dict]:
    return [
        {"actual": float(actual), "predicted": float(predicted)}
        for actual, predicted in zip(np.asarray(y_true)[:limit], np.asarray(y_pred)[:limit])
    ]


def _dataset_summary(frame: pd.DataFrame, csv_paths: list[Path]) -> dict:
    return {
        "source": "Corrected enriched Sindh GEE climate/remote-sensing dataset" if not csv_paths else "Existing local Sindh GEE remote sensing CSV files",
        "csv_files": len(csv_paths),
        "rows": int(len(frame)),
        "grids": int(frame["grid_id"].nunique()),
        "date_min": str(frame["date"].min().date()),
        "date_max": str(frame["date"].max().date()),
    }


def _claim(metrics: dict, beat: dict) -> str:
    beaten = [key for key, value in beat.items() if value]
    if beaten:
        return f"Strict next-month forecasting beat the base paper on {beaten}."
    return (
        "Strict next-month forecasting did not beat the base paper. "
        f"Best strict result: R2={metrics['r2']:.4f}, RMSE={metrics['rmse']:.4f}, MAE={metrics['mae']:.4f}."
    )


def _severity_label(vhi: float) -> str:
    if vhi < 0.20:
        return "Extreme Drought"
    if vhi < 0.35:
        return "Severe Drought"
    if vhi < 0.50:
        return "Moderate Drought"
    if vhi < 0.65:
        return "Mild Drought"
    return "No Drought"


def _json_ready(value):
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value
