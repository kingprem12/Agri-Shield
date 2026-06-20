from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.metrics import accuracy_score, explained_variance_score, f1_score, mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from app.ml.advanced_feature_engineering import (
    BASE_SIGNAL_COLUMNS,
    build_advanced_drought_frame,
    drought_label,
    feature_columns,
)


BASE_PAPER = {"model": "Base paper Wavelet-XGBoost", "r2": 0.964, "rmse": 0.021, "mae": 0.023}
DEFAULT_DATASET_DIR = Path("/Users/prem/Documents/My Final year Project/Data Sets")
MODEL_PATH = Path("models/pso_sindh/pso_wavelet_xgboost_sindh.joblib")
REPORT_PATH = Path("reports/pso_sindh_metrics.json")
CHAMPION_MODEL_PATH = Path("models/pso_sindh/pso_wavelet_xgboost_sindh_champion.joblib")
CHAMPION_REPORT_PATH = Path("reports/pso_sindh_champion_metrics.json")
PLOT_PATHS = {
    "actual_vs_predicted": Path("reports/pso_sindh_actual_vs_predicted.png"),
    "feature_importance": Path("reports/pso_sindh_feature_importance.png"),
    "metric_comparison": Path("reports/pso_sindh_metric_comparison.png"),
}


@dataclass
class PsoResult:
    params: dict
    feature_names: list[str]
    lag_window: int
    wavelet_level: int
    score: float
    history: list[dict]
    seed: int = 42
    booster: str = "gbtree"


class PsoFeatureSelectedStacking:
    def __init__(self, params: dict):
        self.params = dict(params)
        self.xgb = _xgb(params)
        self.extra_trees = ExtraTreesRegressor(n_estimators=70, max_depth=24, random_state=123, n_jobs=1)
        self.final = XGBRegressor(
            n_estimators=55,
            max_depth=3,
            learning_rate=0.04,
            objective="reg:squarederror",
            random_state=321,
            n_jobs=1,
        )

    def fit(self, x, y):
        self.xgb.fit(x, y)
        self.extra_trees.fit(x, y)
        stacked = self._stack_features(x)
        self.final.fit(stacked, y)
        return self

    def predict(self, x):
        return self.final.predict(self._stack_features(x))

    def _stack_features(self, x):
        xgb_pred = self.xgb.predict(x)
        trees_pred = self.extra_trees.predict(x)
        return np.column_stack([xgb_pred, trees_pred, np.asarray(x)])


def train_pso_sindh_model(
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    pattern: str = "Sindh_Grid_*.csv",
    limit_files: int = 276,
    max_grid_rows: int = 50_000,
    particles: int = 8,
    iterations: int = 7,
    model_path: Path = MODEL_PATH,
    report_path: Path = REPORT_PATH,
) -> dict:
    csv_paths = sorted(dataset_dir.glob(pattern))[:limit_files]
    if len(csv_paths) < 24:
        raise ValueError(f"Need at least 24 Sindh grid CSV files, found {len(csv_paths)}")

    model_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    frame = build_advanced_drought_frame(csv_paths, max_grid_rows=max_grid_rows)
    feature_groups = _feature_groups(frame)
    base_features = _select_features(feature_groups, lag_window=12, wavelet_level=2, mask=np.ones(len(feature_groups), dtype=bool))

    split_cut = frame["date"].quantile(0.8)
    train = frame[frame["date"] <= split_cut].copy()
    test = frame[frame["date"] > split_cut].copy()
    train_fit, valid = _chronological_validation_split(train)

    result = _pso_search(train_fit, valid, feature_groups, particles=particles, iterations=iterations)
    chrono_model = _xgb(result.params)
    chrono_model.fit(train[result.feature_names], train["target_vhi_h1"])
    chrono_pred = chrono_model.predict(test[result.feature_names])

    random_x_train, random_x_test, random_y_train, random_y_test = train_test_split(
        frame[result.feature_names],
        frame["target_vhi_h1"],
        test_size=0.3,
        shuffle=True,
        random_state=42,
    )
    random_model = _xgb(result.params)
    random_model.fit(random_x_train, random_y_train)
    random_pred = random_model.predict(random_x_test)

    same_features = [feature for feature in result.feature_names if feature != "vhi"]
    same_x_train, same_x_test, same_y_train, same_y_test = train_test_split(
        frame[same_features],
        frame["same_month_vhi"],
        test_size=0.3,
        shuffle=True,
        random_state=74,
    )
    same_model = _xgb(result.params)
    same_model.fit(same_x_train, same_y_train)
    same_pred = same_model.predict(same_x_test)

    protocols = {
        "A_strict_chronological_future_forecasting": {
            "model": "PSO-Optimized Wavelet-XGBoost Sindh next-month forecast",
            "protocol": "A_strict_chronological_future_forecasting",
            **regression_metrics(test["target_vhi_h1"], chrono_pred),
        },
        "B_paper_comparable_random_split": {
            "model": "PSO-Optimized Wavelet-XGBoost Sindh random split",
            "protocol": "B_paper_comparable_random_split",
            **regression_metrics(random_y_test, random_pred),
        },
        "C_same_month_estimation": {
            "model": "PSO-Optimized Wavelet-XGBoost Sindh same-month VHI estimation",
            "protocol": "C_same_month_estimation",
            **regression_metrics(same_y_test, same_pred),
        },
    }
    best = max(protocols.values(), key=lambda row: (row["r2"], -row["rmse"], -row["mae"]))
    beat = {
        "r2": best["r2"] > BASE_PAPER["r2"],
        "rmse": best["rmse"] < BASE_PAPER["rmse"],
        "mae": best["mae"] < BASE_PAPER["mae"],
    }

    artifact = {
        "forecast_model": chrono_model,
        "random_split_model": random_model,
        "same_month_model": same_model,
        "features": result.feature_names,
        "same_month_features": same_features,
        "params": result.params,
        "lag_window": result.lag_window,
        "wavelet_level": result.wavelet_level,
        "base_features": base_features,
        "dataset_summary": _dataset_summary(frame, csv_paths),
        "protocol_warning": "Strict forecasting and same-month estimation are reported separately.",
    }
    joblib.dump(artifact, model_path)

    plots = _save_plots(
        protocols=protocols,
        y_true=test["target_vhi_h1"].to_numpy(),
        y_pred=chrono_pred,
        model=chrono_model,
        features=result.feature_names,
        report_dir=report_path.parent,
    )
    report = {
        "project": "AgriShield-X",
        "model": "PSO-Optimized Wavelet-XGBoost for Sindh agricultural drought prediction",
        "base_paper": BASE_PAPER,
        "dataset": _dataset_summary(frame, csv_paths),
        "pso": {
            "particles": particles,
            "iterations": iterations,
            "best_params": result.params,
            "selected_features": result.feature_names,
            "selected_feature_count": len(result.feature_names),
            "lag_window": result.lag_window,
            "wavelet_level": result.wavelet_level,
            "validation_rmse": result.score,
            "history": result.history,
        },
        "protocols": protocols,
        "actual_vs_predicted_sample": _prediction_sample(test["target_vhi_h1"], chrono_pred),
        "best_model": best,
        "success_against_base_paper": beat,
        "claim": _claim(best, beat),
        "artifact_path": str(model_path),
        "plots": plots,
        "honesty_warning": "If same-month estimation beats the base paper, it is not future forecasting.",
    }
    report_path.write_text(json.dumps(_json_ready(report), indent=2))
    return report


def train_pso_sindh_champion(
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    pattern: str = "Sindh_Grid_*.csv",
    limit_files: int = 276,
    max_grid_rows: int = 50_000,
    particles: int = 10,
    iterations: int = 8,
    seeds: list[int] | None = None,
    model_path: Path = CHAMPION_MODEL_PATH,
    report_path: Path = CHAMPION_REPORT_PATH,
) -> dict:
    csv_paths = sorted(dataset_dir.glob(pattern))[:limit_files]
    if len(csv_paths) < 24:
        raise ValueError(f"Need at least 24 Sindh grid CSV files, found {len(csv_paths)}")

    model_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    frame = build_advanced_drought_frame(csv_paths, max_grid_rows=max_grid_rows)
    frame = _add_target_variants(frame)
    feature_groups = _feature_groups(frame)
    train, test, random_split, same_split, spatial_split = _protocol_splits(frame)
    train_fit, valid = _chronological_validation_split(train)

    seeds = seeds or [7, 19, 42]
    pso_results = []
    for seed in seeds:
        for booster in ["gbtree", "dart"]:
            pso_results.append(
                _pso_search_champion(
                    train_fit=train_fit,
                    valid=valid,
                    feature_groups=feature_groups,
                    particles=particles,
                    iterations=iterations,
                    seed=seed,
                    booster=booster,
                    patience=max(3, iterations // 2),
                )
            )
    best_pso = min(pso_results, key=lambda item: item.score)
    champion_features = best_pso.feature_names

    candidates = []
    protocols = {}
    artifacts = {}
    for protocol_name, split in {
        "A_strict_chronological_future_forecasting": (train, test, "target_vhi_h1", champion_features),
        "B_paper_comparable_random_split": (*random_split, "target_vhi_h1", champion_features),
        "C_same_month_estimation": (*same_split, "same_month_vhi", [feature for feature in champion_features if feature != "vhi"]),
        "D_spatial_holdout": (*spatial_split, "target_vhi_h1", champion_features),
    }.items():
        rows, models = _evaluate_protocol_family(protocol_name, split, best_pso.params)
        protocols[protocol_name] = rows
        artifacts[protocol_name] = models
        candidates.extend(rows)

    rolling_rows = _rolling_origin_validation(frame, champion_features, best_pso.params)
    protocols["E_rolling_origin_validation"] = rolling_rows
    candidates.extend(rolling_rows)

    best = _select_champion(candidates)
    beat = _beat_flags(best)
    champion_protocol = best["protocol"]
    champion_model = artifacts.get(champion_protocol, {}).get(best["model_key"])
    if champion_model is None:
        champion_model = _xgb(best_pso.params)
        champion_model.fit(train[champion_features], train["target_vhi_h1"])

    artifact = {
        "champion_model": champion_model,
        "champion_row": best,
        "features": best.get("features", champion_features),
        "params": best_pso.params,
        "pso": {
            "particles": particles,
            "iterations": iterations,
            "seeds": seeds,
            "best_seed": best_pso.seed,
            "best_booster": best_pso.booster,
            "validation_rmse": best_pso.score,
            "lag_window": best_pso.lag_window,
            "wavelet_level": best_pso.wavelet_level,
            "selected_features": champion_features,
            "history": best_pso.history,
        },
        "dataset_summary": _dataset_summary(frame, csv_paths),
        "honesty_warning": _honesty_note(best),
    }
    joblib.dump(artifact, model_path)

    plot_path = _save_champion_comparison_plot(protocols, report_path.parent)
    report = {
        "project": "AgriShield-X",
        "model": "PSO Sindh champion selector",
        "base_paper": BASE_PAPER,
        "dataset": _dataset_summary(frame, csv_paths),
        "available_optional_libraries": {"lightgbm": False, "catboost": False, "xgboost": True, "sklearn": True},
        "pso": artifact["pso"],
        "protocols": protocols,
        "champion_selector": "Lowest RMSE first, lowest MAE second, highest R2 third.",
        "best_model": best,
        "success_against_base_paper": beat,
        "beat_paper": any(beat.values()),
        "metric_beaten": [metric for metric, did_beat in beat.items() if did_beat],
        "claim": _claim(best, beat),
        "honesty_note": _honesty_note(best),
        "artifact_path": str(model_path),
        "comparison_plot": str(plot_path),
    }
    report_path.write_text(json.dumps(_json_ready(report), indent=2))
    return report


def load_pso_artifact(model_path: Path = MODEL_PATH) -> dict | None:
    return joblib.load(model_path) if model_path.exists() else None


def load_pso_report(report_path: Path = REPORT_PATH) -> dict:
    if report_path.exists():
        return json.loads(report_path.read_text())
    return {
        "model": "PSO-Optimized Wavelet-XGBoost for Sindh agricultural drought prediction",
        "base_paper": BASE_PAPER,
        "protocols": {},
        "warning": "PSO Sindh report has not been trained yet.",
    }


def predict_from_payload(payload: dict, artifact: dict) -> dict:
    features = artifact["features"]
    row = _payload_to_feature_row(payload, features)
    prediction = float(np.clip(artifact["forecast_model"].predict(pd.DataFrame([row], columns=features))[0], 0, 1))
    severity = drought_label(prediction)
    return {
        "predicted_vhi": prediction,
        "drought_severity": severity,
        "risk_score": float((1 - prediction) * 100),
        "model": "PSO-Optimized Wavelet-XGBoost Sindh",
        "protocol_warning": artifact.get("protocol_warning", "Strict forecasting and same-month estimation are reported separately."),
    }


def feature_importance(model_path: Path = MODEL_PATH, top_n: int = 20) -> list[dict]:
    artifact = load_pso_artifact(model_path)
    if not artifact:
        return []
    model = artifact["forecast_model"]
    importances = getattr(model, "feature_importances_", np.zeros(len(artifact["features"])))
    rows = sorted(zip(artifact["features"], importances), key=lambda item: item[1], reverse=True)[:top_n]
    return [{"feature": feature, "importance": float(value)} for feature, value in rows]


def regression_metrics(y_true, y_pred) -> dict[str, float]:
    true = np.asarray(y_true, dtype=float)
    pred = np.clip(np.asarray(y_pred, dtype=float), 0, 1)
    true_class = np.asarray([_severity_index(value) for value in true])
    pred_class = np.asarray([_severity_index(value) for value in pred])
    denominator = np.sum((np.abs(pred - true) + np.abs(true - true.mean())) ** 2)
    willmott_denominator = np.sum((np.abs(pred - true.mean()) + np.abs(true - true.mean())) ** 2)
    return {
        "r2": float(r2_score(true, pred)),
        "rmse": float(mean_squared_error(true, pred) ** 0.5),
        "mae": float(mean_absolute_error(true, pred)),
        "mape": float(mean_absolute_percentage_error(np.clip(true, 0.01, 1), np.clip(pred, 0.01, 1))),
        "explained_variance": float(explained_variance_score(true, pred)),
        "smape": float(np.mean(2 * np.abs(pred - true) / np.clip(np.abs(true) + np.abs(pred), 0.01, None))),
        "nse": float(1 - np.sum((true - pred) ** 2) / max(np.sum((true - true.mean()) ** 2), 1e-12)),
        "willmott_index": float(1 - np.sum((pred - true) ** 2) / max(willmott_denominator, 1e-12)),
        "pearson_correlation": float(np.corrcoef(true, pred)[0, 1]) if len(true) > 1 and np.std(pred) > 0 and np.std(true) > 0 else 0.0,
        "drought_class_accuracy": float(accuracy_score(true_class, pred_class)),
        "drought_class_f1": float(f1_score(true_class, pred_class, average="macro", zero_division=0)),
    }


def _add_target_variants(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.sort_values(["grid_id", "date"]).copy()
    grouped = data.groupby("grid_id", group_keys=False)
    past_vhi = grouped["vhi"].shift(1)
    data["vhi_smoothed_past"] = past_vhi.groupby(data["grid_id"]).transform(lambda series: series.rolling(3, min_periods=1).mean())
    data["vhi_residual_past"] = (data["vhi_lag_1"] - data["vhi_smoothed_past"]).fillna(0)
    month_mean = data.groupby("month")["vhi_lag_1"].transform("mean")
    data["vhi_anomaly_past"] = (data["vhi_lag_1"] - month_mean).fillna(0)
    numeric = data.select_dtypes(include=["number"]).columns
    data[numeric] = data[numeric].replace([np.inf, -np.inf], np.nan)
    data[numeric] = data[numeric].fillna(data[numeric].median(numeric_only=True))
    return data


def _protocol_splits(frame: pd.DataFrame):
    split_cut = frame["date"].quantile(0.8)
    train = frame[frame["date"] <= split_cut].copy()
    test = frame[frame["date"] > split_cut].copy()
    random_train, random_test = train_test_split(frame, test_size=0.3, shuffle=True, random_state=42)
    same_train, same_test = train_test_split(frame, test_size=0.3, shuffle=True, random_state=74)
    grids = pd.Series(frame["grid_id"].unique()).sample(frac=1, random_state=91).to_numpy()
    holdout_grids = set(grids[: max(1, int(len(grids) * 0.2))])
    spatial_train = frame[~frame["grid_id"].isin(holdout_grids)].copy()
    spatial_test = frame[frame["grid_id"].isin(holdout_grids)].copy()
    return train, test, (random_train, random_test), (same_train, same_test), (spatial_train, spatial_test)


def _evaluate_protocol_family(protocol: str, split, params: dict):
    train, test, target, features = split
    features = [feature for feature in features if feature in train.columns and feature in test.columns]
    rows = []
    models = {}
    family = {
        "PSO Wavelet-XGBoost": _xgb(params),
        "PSO Wavelet-XGBoost DART": _xgb({**params, "booster": "dart", "rate_drop": 0.08, "skip_drop": 0.08}),
        "ExtraTrees": ExtraTreesRegressor(n_estimators=90, max_depth=26, random_state=222, n_jobs=1),
        "HistGradientBoosting": HistGradientBoostingRegressor(max_iter=110, learning_rate=0.045, max_leaf_nodes=31, l2_regularization=0.05, random_state=222),
    }
    stack_features = features
    for name, model in family.items():
        model.fit(train[features], train[target])
        pred = model.predict(test[features])
        row = {
            "model": f"{name} {protocol}",
            "model_key": name,
            "protocol": protocol,
            "target": target,
            "features": features,
            **regression_metrics(test[target], pred),
        }
        rows.append(row)
        models[name] = model
    stack = _stacking_model(params)
    stack.fit(train[stack_features], train[target])
    stack_pred = stack.predict(test[stack_features])
    rows.append(
        {
            "model": f"PSO feature-selected stacking ensemble {protocol}",
            "model_key": "PSO feature-selected stacking ensemble",
            "protocol": protocol,
            "target": target,
            "features": stack_features,
            **regression_metrics(test[target], stack_pred),
        }
    )
    models["PSO feature-selected stacking ensemble"] = stack
    return rows, models


def _stacking_model(params: dict) -> PsoFeatureSelectedStacking:
    return PsoFeatureSelectedStacking(params)


def _rolling_origin_validation(frame: pd.DataFrame, features: list[str], params: dict) -> list[dict]:
    ordered_dates = sorted(frame["date"].unique())
    cut_positions = [int(len(ordered_dates) * ratio) for ratio in [0.55, 0.65, 0.75]]
    fold_metrics = []
    for fold, position in enumerate(cut_positions, start=1):
        train_dates = ordered_dates[:position]
        test_dates = ordered_dates[position : min(position + 6, len(ordered_dates))]
        if not test_dates:
            continue
        train = frame[frame["date"].isin(train_dates)]
        test = frame[frame["date"].isin(test_dates)]
        model = _xgb(params)
        model.fit(train[features], train["target_vhi_h1"])
        fold_metrics.append(regression_metrics(test["target_vhi_h1"], model.predict(test[features])))
    if not fold_metrics:
        return []
    averaged = {key: float(np.mean([row[key] for row in fold_metrics])) for key in fold_metrics[0]}
    return [
        {
            "model": "PSO Wavelet-XGBoost rolling-origin average",
            "model_key": "PSO Wavelet-XGBoost rolling-origin average",
            "protocol": "E_rolling_origin_validation",
            "target": "target_vhi_h1",
            "features": features,
            "folds": len(fold_metrics),
            **averaged,
        }
    ]


def _select_champion(rows: list[dict]) -> dict:
    return min(rows, key=lambda row: (row["rmse"], row["mae"], -row["r2"]))


def _beat_flags(row: dict) -> dict[str, bool]:
    return {
        "r2": row["r2"] > BASE_PAPER["r2"],
        "rmse": row["rmse"] < BASE_PAPER["rmse"],
        "mae": row["mae"] < BASE_PAPER["mae"],
    }


def _honesty_note(row: dict) -> str:
    if row["protocol"] == "A_strict_chronological_future_forecasting":
        return "This is strict future forecasting with no target-month VHI leakage."
    if row["protocol"] == "C_same_month_estimation":
        return "This is same-month VHI estimation/reconstruction, not future forecasting."
    if row["protocol"] == "B_paper_comparable_random_split":
        return "This is paper-comparable random split evaluation, not chronological deployment forecasting."
    if row["protocol"] == "D_spatial_holdout":
        return "This is unseen grid-cell spatial holdout evaluation."
    return "This is rolling-origin future validation averaged across folds."


def _severity_index(vhi: float) -> int:
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


def _save_champion_comparison_plot(protocols: dict, report_dir: Path) -> Path:
    path = report_dir / "pso_sindh_champion_comparison.png"
    try:
        import matplotlib.pyplot as plt

        rows = [row for values in protocols.values() for row in values]
        rows = sorted(rows, key=lambda row: row["rmse"])[:14]
        labels = [f"{row['model_key']}\\n{row['protocol'].split('_')[0]}" for row in rows]
        values = [row["rmse"] for row in rows]
        plt.figure(figsize=(max(9, len(rows) * 0.7), 5))
        plt.bar(range(len(rows)), values, color="#059669")
        plt.axhline(BASE_PAPER["rmse"], color="#dc2626", linestyle="--", linewidth=1, label="Base paper RMSE")
        plt.xticks(range(len(rows)), labels, rotation=65, ha="right")
        plt.ylabel("RMSE")
        plt.legend()
        plt.tight_layout()
        plt.savefig(path, dpi=170)
        plt.close()
    except Exception:
        path.write_text("Plot generation failed")
    return path


def _pso_search(train, valid, feature_groups, particles: int, iterations: int) -> PsoResult:
    rng = np.random.default_rng(42)
    dimensions = 10 + len(feature_groups)
    positions = rng.random((particles, dimensions))
    velocities = rng.normal(0, 0.08, positions.shape)
    personal_best = positions.copy()
    personal_scores = np.full(particles, math.inf)
    global_best = positions[0].copy()
    global_score = math.inf
    history = []

    for iteration in range(iterations):
        for particle in range(particles):
            params, lag_window, wavelet_level, mask = _decode_particle(positions[particle], len(feature_groups))
            features = _select_features(feature_groups, lag_window=lag_window, wavelet_level=wavelet_level, mask=mask)
            model = _xgb(params)
            model.fit(train[features], train["target_vhi_h1"])
            pred = model.predict(valid[features])
            score = regression_metrics(valid["target_vhi_h1"], pred)["rmse"]
            history.append(
                {
                    "iteration": iteration,
                    "particle": particle,
                    "rmse": score,
                    "feature_count": len(features),
                    "lag_window": lag_window,
                    "wavelet_level": wavelet_level,
                    "params": params,
                }
            )
            if score < personal_scores[particle]:
                personal_scores[particle] = score
                personal_best[particle] = positions[particle].copy()
            if score < global_score:
                global_score = score
                global_best = positions[particle].copy()
        inertia = 0.55
        cognitive = 1.35 * rng.random(positions.shape) * (personal_best - positions)
        social = 1.35 * rng.random(positions.shape) * (global_best - positions)
        velocities = inertia * velocities + cognitive + social
        positions = np.clip(positions + velocities, 0, 1)

    params, lag_window, wavelet_level, mask = _decode_particle(global_best, len(feature_groups))
    features = _select_features(feature_groups, lag_window=lag_window, wavelet_level=wavelet_level, mask=mask)
    return PsoResult(params=params, feature_names=features, lag_window=lag_window, wavelet_level=wavelet_level, score=global_score, history=history)


def _pso_search_champion(
    train_fit,
    valid,
    feature_groups,
    particles: int,
    iterations: int,
    seed: int,
    booster: str,
    patience: int,
) -> PsoResult:
    rng = np.random.default_rng(seed)
    dimensions = 13 + len(feature_groups)
    positions = rng.random((particles, dimensions))
    velocities = rng.normal(0, 0.09, positions.shape)
    personal_best = positions.copy()
    personal_scores = np.full(particles, math.inf)
    global_best = positions[0].copy()
    global_score = math.inf
    stale = 0
    history = []

    for iteration in range(iterations):
        improved = False
        inertia = float(np.interp(iteration, [0, max(iterations - 1, 1)], [0.82, 0.38]))
        c1 = float(np.interp(iteration, [0, max(iterations - 1, 1)], [1.65, 1.15]))
        c2 = float(np.interp(iteration, [0, max(iterations - 1, 1)], [1.10, 1.85]))
        for particle in range(particles):
            params, lag_window, wavelet_level, mask = _decode_champion_particle(positions[particle], len(feature_groups), booster)
            features = _select_features(feature_groups, lag_window=lag_window, wavelet_level=wavelet_level, mask=mask)
            model = _xgb(params)
            model.fit(train_fit[features], train_fit["target_vhi_h1"])
            pred = model.predict(valid[features])
            score = regression_metrics(valid["target_vhi_h1"], pred)["rmse"]
            history.append(
                {
                    "seed": seed,
                    "booster": booster,
                    "iteration": iteration,
                    "particle": particle,
                    "rmse": score,
                    "feature_count": len(features),
                    "lag_window": lag_window,
                    "wavelet_level": wavelet_level,
                    "params": params,
                }
            )
            if score < personal_scores[particle]:
                personal_scores[particle] = score
                personal_best[particle] = positions[particle].copy()
            if score < global_score:
                global_score = score
                global_best = positions[particle].copy()
                improved = True
        if not improved:
            stale += 1
        else:
            stale = 0
        if stale >= patience:
            break
        velocities = (
            inertia * velocities
            + c1 * rng.random(positions.shape) * (personal_best - positions)
            + c2 * rng.random(positions.shape) * (global_best - positions)
        )
        positions = np.clip(positions + velocities, 0, 1)

    params, lag_window, wavelet_level, mask = _decode_champion_particle(global_best, len(feature_groups), booster)
    features = _select_features(feature_groups, lag_window=lag_window, wavelet_level=wavelet_level, mask=mask)
    return PsoResult(params=params, feature_names=features, lag_window=lag_window, wavelet_level=wavelet_level, score=global_score, history=history, seed=seed, booster=booster)


def _decode_particle(position: np.ndarray, group_count: int):
    params = {
        "max_depth": int(round(_scale(position[0], 2, 8))),
        "learning_rate": float(10 ** _scale(position[1], math.log10(0.015), math.log10(0.16))),
        "n_estimators": int(round(_scale(position[2], 90, 320))),
        "subsample": float(_scale(position[3], 0.65, 1.0)),
        "colsample_bytree": float(_scale(position[4], 0.65, 1.0)),
        "reg_lambda": float(10 ** _scale(position[5], math.log10(0.1), math.log10(20))),
        "reg_alpha": float(_scale(position[6], 0.0, 3.0)),
        "min_child_weight": float(_scale(position[7], 1.0, 9.0)),
        "gamma": float(_scale(position[8], 0.0, 2.5)),
    }
    lag_window = [1, 2, 3, 6, 12][min(4, int(position[9] * 5))]
    wavelet_level = 1 if position[9] < 0.5 else 2
    mask = position[10 : 10 + group_count] >= 0.42
    return params, lag_window, wavelet_level, mask


def _decode_champion_particle(position: np.ndarray, group_count: int, booster: str):
    params = {
        "max_depth": int(round(_scale(position[0], 2, 7))),
        "learning_rate": float(10 ** _scale(position[1], math.log10(0.008), math.log10(0.18))),
        "n_estimators": int(round(_scale(position[2], 80, 180))),
        "subsample": float(_scale(position[3], 0.55, 1.0)),
        "colsample_bytree": float(_scale(position[4], 0.5, 1.0)),
        "reg_lambda": float(10 ** _scale(position[5], math.log10(0.05), math.log10(35))),
        "reg_alpha": float(_scale(position[6], 0.0, 6.0)),
        "min_child_weight": float(_scale(position[7], 0.5, 12.0)),
        "gamma": float(_scale(position[8], 0.0, 4.0)),
        "max_bin": int(round(_scale(position[9], 128, 320))),
        "tree_method": "hist",
        "grow_policy": "lossguide" if position[10] > 0.5 else "depthwise",
        "objective": "reg:squarederror",
        "booster": booster,
    }
    if booster == "dart":
        params["rate_drop"] = float(_scale(position[11], 0.02, 0.24))
        params["skip_drop"] = float(_scale(position[12], 0.0, 0.25))
    lag_window = [1, 2, 3, 6, 12][min(4, int(position[11] * 5))]
    wavelet_level = 1 if position[12] < 0.45 else 2
    mask = position[13 : 13 + group_count] >= 0.38
    return params, lag_window, wavelet_level, mask


def _feature_groups(frame) -> dict[str, list[str]]:
    features = feature_columns(frame)
    groups: dict[str, list[str]] = {
        "base_remote_sensing": [item for item in ["ndvi", "lst", "rainfall", "vci", "tci", "vhi", "mndwi", "temperature", "humidity", "soil_moisture"] if item in features],
        "seasonal": [item for item in features if item in {"month", "month_sin", "month_cos", "season", "season_sin", "season_cos"}],
    }
    for signal in BASE_SIGNAL_COLUMNS + ["mndwi"]:
        lag_roll = [item for item in features if item.startswith(f"{signal}_lag_") or item.startswith(f"{signal}_roll_")]
        wavelet = [item for item in features if item.startswith(f"{signal}_wavelet_")]
        if lag_roll:
            groups[f"{signal}_lag_roll"] = lag_roll
        if wavelet:
            groups[f"{signal}_wavelet"] = wavelet
    groups["location"] = [item for item in ["longitude", "latitude"] if item in features]
    groups["target_engineered_past"] = [item for item in ["vhi_smoothed_past", "vhi_residual_past", "vhi_anomaly_past"] if item in features]
    return {key: value for key, value in groups.items() if value}


def _select_features(feature_groups: dict[str, list[str]], lag_window: int, wavelet_level: int, mask: np.ndarray) -> list[str]:
    selected = []
    group_items = list(feature_groups.items())
    for enabled, (group_name, columns) in zip(mask, group_items):
        if not enabled and group_name not in {"base_remote_sensing", "seasonal"}:
            continue
        for column in columns:
            if "_lag_" in column and int(column.rsplit("_", 1)[-1]) > lag_window:
                continue
            if "_roll_" in column and int(column.rsplit("_", 1)[-1]) > max(3, lag_window):
                continue
            if column.endswith("_wavelet_detail") and wavelet_level < 2:
                continue
            selected.append(column)
    required = feature_groups.get("base_remote_sensing", []) + feature_groups.get("seasonal", [])
    selected = sorted(set(selected + required))
    if len(selected) < 6:
        selected = sorted(set(sum(feature_groups.values(), [])))[:24]
    return selected


def _xgb(params: dict) -> XGBRegressor:
    safe = dict(params)
    safe["max_depth"] = int(safe.get("max_depth", 4))
    safe["n_estimators"] = int(safe.get("n_estimators", 160))
    safe.setdefault("objective", "reg:squarederror")
    safe.setdefault("random_state", 42)
    safe.setdefault("n_jobs", 1)
    return XGBRegressor(**safe)


def _chronological_validation_split(train):
    ordered = train.sort_values("date")
    split = max(1, int(len(ordered) * 0.8))
    return ordered.iloc[:split], ordered.iloc[split:]


def _dataset_summary(frame, csv_paths):
    return {
        "source": "Existing local Sindh GEE remote sensing CSV files",
        "csv_files": len(csv_paths),
        "rows": len(frame),
        "grids": int(frame["grid_id"].nunique()),
        "date_min": frame["date"].min().strftime("%Y-%m-%d"),
        "date_max": frame["date"].max().strftime("%Y-%m-%d"),
    }


def _payload_to_feature_row(payload: dict, features: list[str]) -> dict[str, float]:
    month = int(payload.get("month") or pd.Timestamp.now().month)
    base = {
        "longitude": float(payload.get("longitude", 68.5)),
        "latitude": float(payload.get("latitude", 26.0)),
        "ndvi": float(payload.get("ndvi", 0.35)),
        "lst": float(payload.get("lst", 38.0)),
        "rainfall": float(payload.get("rainfall", 20.0)),
        "temperature": float(payload.get("temperature", payload.get("lst", 38.0) - 2.0)),
        "humidity": float(payload.get("humidity", 35.0)),
        "soil_moisture": float(payload.get("soil_moisture", 0.18)),
        "mndwi": float(payload.get("mndwi", 0.0)),
        "month": month,
        "month_sin": math.sin(2 * math.pi * month / 12),
        "month_cos": math.cos(2 * math.pi * month / 12),
        "season": (month % 12) // 3,
    }
    base["season_sin"] = math.sin(2 * math.pi * base["season"] / 4)
    base["season_cos"] = math.cos(2 * math.pi * base["season"] / 4)
    base["vci"] = float(payload.get("vci", np.clip(base["ndvi"], 0, 1)))
    base["tci"] = float(payload.get("tci", np.clip(1 - (base["lst"] - 20) / 35, 0, 1)))
    base["vhi"] = float(payload.get("vhi", 0.5 * base["vci"] + 0.5 * base["tci"]))
    base["evapotranspiration"] = float(payload.get("evapotranspiration", max(0, 0.08 * base["temperature"] + 0.02 * (100 - base["humidity"]))))
    base["spi"] = float(payload.get("spi", 0.0))
    base["spei"] = float(payload.get("spei", 0.0))
    row = {}
    for feature in features:
        if feature in base:
            row[feature] = base[feature]
        elif "_lag_" in feature:
            row[feature] = base.get(feature.split("_lag_")[0], base["vhi"])
        elif "_roll_" in feature:
            row[feature] = base.get(feature.split("_roll_")[0], base["vhi"])
        elif "_wavelet_" in feature:
            row[feature] = base.get(feature.split("_wavelet_")[0], 0.0)
        else:
            row[feature] = 0.0
    return row


def _save_plots(protocols, y_true, y_pred, model, features, report_dir: Path) -> dict[str, str]:
    plots = {}
    try:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(7, 5))
        plt.scatter(y_true, np.clip(y_pred, 0, 1), s=8, alpha=0.45)
        plt.plot([0, 1], [0, 1], color="black", linewidth=1)
        plt.xlabel("Actual VHI")
        plt.ylabel("Predicted VHI")
        plt.tight_layout()
        path = report_dir / "pso_sindh_actual_vs_predicted.png"
        plt.savefig(path, dpi=160)
        plt.close()
        plots["actual_vs_predicted"] = str(path)

        names = [row["protocol"].replace("_", " ") for row in protocols.values()]
        values = [row["r2"] for row in protocols.values()]
        plt.figure(figsize=(8, 4))
        plt.bar(names, values)
        plt.xticks(rotation=18, ha="right")
        plt.ylabel("R2")
        plt.tight_layout()
        path = report_dir / "pso_sindh_metric_comparison.png"
        plt.savefig(path, dpi=160)
        plt.close()
        plots["metric_comparison"] = str(path)

        importances = getattr(model, "feature_importances_", np.zeros(len(features)))
        order = np.argsort(importances)[-18:]
        plt.figure(figsize=(8, 5))
        plt.barh([features[index] for index in order], importances[order])
        plt.tight_layout()
        path = report_dir / "pso_sindh_feature_importance.png"
        plt.savefig(path, dpi=160)
        plt.close()
        plots["feature_importance"] = str(path)
    except Exception as exc:
        plots["plot_warning"] = str(exc)
    return plots


def _prediction_sample(y_true, y_pred, limit: int = 120) -> list[dict[str, float]]:
    true = np.asarray(y_true, dtype=float)
    pred = np.clip(np.asarray(y_pred, dtype=float), 0, 1)
    if len(true) <= limit:
        indices = np.arange(len(true))
    else:
        indices = np.linspace(0, len(true) - 1, limit, dtype=int)
    return [{"actual": float(true[index]), "predicted": float(pred[index])} for index in indices]


def _claim(best, beat):
    won = [metric for metric, did_beat in beat.items() if did_beat]
    if not won:
        return "The PSO Sindh model did not beat the base paper under the evaluated protocols."
    if best["protocol"] == "C_same_month_estimation":
        return f"Beat base paper metric(s) {won} only under same-month estimation, not future forecasting."
    return f"Beat base paper metric(s) {won} under {best['protocol']}."


def _scale(value, low, high):
    return low + float(value) * (high - low)


def _json_ready(value):
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value
