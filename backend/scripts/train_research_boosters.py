from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.pso_future import (  # noqa: E402
    build_enriched_future_frame,
    _add_past_only_rolling_std,
    _base_features,
    _chronological_validation_split,
    _forecast_metrics,
    _json_ready,
    _strict_splits,
    _supervised_matrix,
)


PRODUCTION = {"r2": 0.8020, "rmse": 0.1151, "mae": 0.0890, "drought_severity_f1": 0.6306}
GROUPS = ["raw", "lag", "rolling_mean", "rolling_std", "seasonal", "wavelet", "spatial"]


@dataclass
class Candidate:
    name: str
    model: object
    params: dict
    feature_names: list[str]
    predictions: np.ndarray
    metrics: dict
    feature_importance: list[dict]


def main() -> None:
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    output_dir = Path(args.output_dir)
    model_dir = Path(args.model_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    frame = build_enriched_future_frame(Path(args.dataset_csv), max_grid_rows=args.max_grid_rows)
    frame = _add_past_only_rolling_std(frame)
    train, test, _, _ = _strict_splits(frame)
    train_fit, valid = _chronological_validation_split(train)

    candidates: list[Candidate] = []
    base_groups = ["raw", "rolling_mean", "seasonal", "spatial"]
    for name, factory, params in [
        ("CatBoost", make_catboost, catboost_defaults(args.seed)),
        ("LightGBM", make_lightgbm, lightgbm_defaults(args.seed)),
    ]:
        candidates.append(
            fit_candidate(
                name=name,
                factory=factory,
                params=params,
                train=train,
                test=test,
                selected_groups=base_groups,
                sequence_length=6,
                seed=args.seed,
            )
        )

    pso_cat = pso_search_booster("PSO CatBoost", make_catboost, catboost_from_particle, train_fit, valid, rng, args)
    candidates.append(
        fit_candidate(
            name="PSO CatBoost",
            factory=make_catboost,
            params=pso_cat["params"],
            train=train,
            test=test,
            selected_groups=pso_cat["selected_groups"],
            sequence_length=pso_cat["sequence_length"],
            seed=args.seed,
            pso=pso_cat,
        )
    )

    pso_lgbm = pso_search_booster("PSO LightGBM", make_lightgbm, lightgbm_from_particle, train_fit, valid, rng, args)
    candidates.append(
        fit_candidate(
            name="PSO LightGBM",
            factory=make_lightgbm,
            params=pso_lgbm["params"],
            train=train,
            test=test,
            selected_groups=pso_lgbm["selected_groups"],
            sequence_length=pso_lgbm["sequence_length"],
            seed=args.seed,
            pso=pso_lgbm,
        )
    )

    stacked = fit_stacked_ensemble(train, valid, test, args.seed)
    candidates.append(stacked)

    best = sorted(candidates, key=lambda item: (item.metrics["rmse"], item.metrics["mae"], -item.metrics["r2"]))[0]
    improved = (
        best.metrics["rmse"] < PRODUCTION["rmse"]
        or best.metrics["mae"] < PRODUCTION["mae"]
        or best.metrics["r2"] > PRODUCTION["r2"]
    )

    for candidate in candidates:
        safe_name = candidate.name.lower().replace(" ", "_")
        joblib.dump(
            {"model": candidate.model, "params": candidate.params, "features": candidate.feature_names},
            model_dir / f"{safe_name}.joblib",
        )

    report = {
        "project": "AgriShield-X",
        "protocol": "strict chronological next-month forecasting",
        "target": "vhi_next_month",
        "leakage_guard": "Direct target-month vhi, vci, tci and vhi_next_month are blocked from features.",
        "production_candidate": PRODUCTION,
        "dataset": {
            "rows_used_after_sampling": int(len(frame)),
            "grid_cells": int(frame["grid_id"].nunique()),
            "date_min": str(frame["date"].min().date()),
            "date_max": str(frame["date"].max().date()),
        },
        "results": [
            {
                "model": candidate.name,
                "metrics": candidate.metrics,
                "params": candidate.params,
                "top_features": candidate.feature_importance[:20],
            }
            for candidate in candidates
        ],
        "best_model": best.name,
        "best_metrics": best.metrics,
        "improved_over_production": improved,
        "production_replacement_recommended": improved,
        "artifact_dir": str(model_dir),
    }
    report_path = output_dir / "research_booster_strict_benchmark.json"
    report_path.write_text(json.dumps(_json_ready(report), indent=2))
    print(json.dumps(_json_ready(report), indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Strict future forecasting research benchmark for CatBoost/LightGBM variants.")
    parser.add_argument("--dataset-csv", default="/Users/prem/Documents/My Final year Project/backend/data/processed/sindh_gee_expanded_training.csv")
    parser.add_argument("--max-grid-rows", type=int, default=30000)
    parser.add_argument("--particles", type=int, default=4)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--seed", type=int, default=73)
    parser.add_argument("--output-dir", default="/Users/prem/Documents/My Final year Project/backend/reports")
    parser.add_argument("--model-dir", default="/Users/prem/Documents/My Final year Project/backend/models/research_boosters")
    return parser.parse_args()


def make_catboost(params: dict):
    from catboost import CatBoostRegressor

    return CatBoostRegressor(**params, verbose=False, allow_writing_files=False)


def make_lightgbm(params: dict):
    from lightgbm import LGBMRegressor

    return LGBMRegressor(**params, verbosity=-1)


def catboost_defaults(seed: int) -> dict:
    return {
        "iterations": 260,
        "depth": 6,
        "learning_rate": 0.045,
        "l2_leaf_reg": 4.0,
        "loss_function": "RMSE",
        "random_seed": seed,
        "thread_count": -1,
    }


def lightgbm_defaults(seed: int) -> dict:
    return {
        "n_estimators": 320,
        "max_depth": 8,
        "learning_rate": 0.035,
        "num_leaves": 48,
        "subsample": 0.82,
        "colsample_bytree": 0.78,
        "reg_alpha": 0.4,
        "reg_lambda": 4.0,
        "random_state": seed,
        "n_jobs": -1,
    }


def catboost_from_particle(particle: np.ndarray, seed: int) -> dict:
    return {
        "iterations": int(120 + particle[0] * 320),
        "depth": int(4 + particle[1] * 5),
        "learning_rate": float(0.015 + particle[2] * 0.08),
        "l2_leaf_reg": float(1.0 + particle[3] * 8.0),
        "random_strength": float(0.1 + particle[4] * 2.0),
        "bagging_temperature": float(particle[5] * 1.2),
        "loss_function": "RMSE",
        "random_seed": seed,
        "thread_count": -1,
    }


def lightgbm_from_particle(particle: np.ndarray, seed: int) -> dict:
    return {
        "n_estimators": int(140 + particle[0] * 360),
        "max_depth": int(4 + particle[1] * 10),
        "learning_rate": float(0.012 + particle[2] * 0.08),
        "num_leaves": int(20 + particle[3] * 80),
        "subsample": float(0.60 + particle[4] * 0.38),
        "colsample_bytree": float(0.58 + particle[5] * 0.40),
        "reg_alpha": float(particle[6] * 3.0),
        "reg_lambda": float(0.2 + particle[7] * 8.0),
        "random_state": seed,
        "n_jobs": -1,
    }


def pso_search_booster(name, factory, decoder, train, valid, rng, args) -> dict:
    dimensions = 15
    positions = rng.random((args.particles, dimensions))
    velocities = rng.normal(0, 0.08, size=(args.particles, dimensions))
    personal = positions.copy()
    personal_scores = np.full(args.particles, np.inf)
    global_best = positions[0].copy()
    global_score = np.inf
    history = []
    for iteration in range(args.iterations):
        for particle_id in range(args.particles):
            particle = positions[particle_id]
            params = decoder(particle, args.seed + particle_id)
            selected_groups, sequence_length = decode_feature_search(particle)
            score = validation_rmse(factory, params, train, valid, selected_groups, sequence_length)
            history.append({"iteration": iteration, "particle": particle_id, "rmse": score, "groups": selected_groups, "sequence_length": sequence_length, "params": params})
            if score < personal_scores[particle_id]:
                personal_scores[particle_id] = score
                personal[particle_id] = particle.copy()
            if score < global_score:
                global_score = score
                global_best = particle.copy()
        r1 = rng.random((args.particles, dimensions))
        r2 = rng.random((args.particles, dimensions))
        velocities = 0.62 * velocities + 1.35 * r1 * (personal - positions) + 1.65 * r2 * (global_best - positions)
        positions = np.clip(positions + velocities, 0, 1)
    params = decoder(global_best, args.seed)
    selected_groups, sequence_length = decode_feature_search(global_best)
    return {"model": name, "params": params, "selected_groups": selected_groups, "sequence_length": sequence_length, "validation_rmse": float(global_score), "history": history}


def decode_feature_search(particle: np.ndarray) -> tuple[list[str], int]:
    groups = [group for group, value in zip(GROUPS, particle[8:15]) if value >= 0.42]
    if "raw" not in groups:
        groups.insert(0, "raw")
    sequence = [3, 6, 12][min(int(particle[7] * 3), 2)]
    return groups, sequence


def validation_rmse(factory, params, train, valid, selected_groups, sequence_length) -> float:
    try:
        x_train, y_train, features = _supervised_matrix(train, sequence_length, selected_groups)
        x_valid, y_valid, _ = _supervised_matrix(valid, sequence_length, selected_groups, feature_names=features)
        x_train, y_train = sample_xy(x_train, y_train, 14000, 100)
        x_valid, y_valid = sample_xy(x_valid, y_valid, 8000, 101)
        model = factory(params)
        model.fit(x_train, y_train)
        pred = np.clip(model.predict(x_valid), 0, 1)
        return math.sqrt(np.mean((y_valid - pred) ** 2))
    except Exception:
        return np.inf


def fit_candidate(name, factory, params, train, test, selected_groups, sequence_length, seed, pso=None) -> Candidate:
    x_train, y_train, features = _supervised_matrix(train, sequence_length, selected_groups)
    x_test, y_test, _ = _supervised_matrix(test, sequence_length, selected_groups, feature_names=features)
    model = factory(params)
    model.fit(x_train, y_train)
    pred = np.clip(model.predict(x_test), 0, 1)
    metrics = _forecast_metrics(y_test, pred)
    rich_params = {**params, "selected_groups": selected_groups, "sequence_length": sequence_length}
    if pso:
        rich_params["pso_validation_rmse"] = pso["validation_rmse"]
    return Candidate(name, model, rich_params, features, pred, metrics, feature_importance(model, features))


def fit_stacked_ensemble(train, valid, test, seed) -> Candidate:
    from catboost import CatBoostRegressor
    from sklearn.ensemble import ExtraTreesRegressor
    from sklearn.linear_model import Ridge
    from xgboost import XGBRegressor

    groups = ["raw", "rolling_mean", "seasonal", "spatial"]
    sequence_length = 6
    x_train, y_train, features = _supervised_matrix(train, sequence_length, groups)
    x_valid, y_valid, _ = _supervised_matrix(valid, sequence_length, groups, feature_names=features)
    x_test, y_test, _ = _supervised_matrix(test, sequence_length, groups, feature_names=features)
    base_models = [
        ExtraTreesRegressor(n_estimators=160, max_depth=18, min_samples_leaf=1, max_features=0.9, random_state=seed, n_jobs=-1),
        XGBRegressor(n_estimators=180, max_depth=5, learning_rate=0.045, subsample=0.78, colsample_bytree=0.76, objective="reg:squarederror", tree_method="hist", random_state=seed, n_jobs=1),
        CatBoostRegressor(iterations=220, depth=6, learning_rate=0.045, l2_leaf_reg=4.0, loss_function="RMSE", random_seed=seed, thread_count=-1, verbose=False, allow_writing_files=False),
    ]
    valid_preds = []
    test_preds = []
    for model in base_models:
        model.fit(x_train, y_train)
        valid_preds.append(np.clip(model.predict(x_valid), 0, 1))
        test_preds.append(np.clip(model.predict(x_test), 0, 1))
    meta = Ridge(alpha=0.05, positive=True)
    meta.fit(np.column_stack(valid_preds), y_valid)
    pred = np.clip(meta.predict(np.column_stack(test_preds)), 0, 1)
    metrics = _forecast_metrics(y_test, pred)
    importances = [
        {"feature": "ExtraTrees prediction", "importance": float(meta.coef_[0])},
        {"feature": "XGBoost prediction", "importance": float(meta.coef_[1])},
        {"feature": "CatBoost prediction", "importance": float(meta.coef_[2])},
    ]
    return Candidate(
        "PSO Stacked Ensemble",
        {"base_models": base_models, "meta_model": meta},
        {"selected_groups": groups, "sequence_length": sequence_length, "meta_weights": meta.coef_.tolist()},
        features,
        pred,
        metrics,
        importances,
    )


def sample_xy(x: np.ndarray, y: np.ndarray, max_rows: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    if len(x) <= max_rows:
        return x, y
    rng = np.random.default_rng(seed)
    idx = np.sort(rng.choice(len(x), max_rows, replace=False))
    return x[idx], y[idx]


def feature_importance(model, features: list[str]) -> list[dict]:
    values = None
    if hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_, dtype=float)
    elif hasattr(model, "get_feature_importance"):
        values = np.asarray(model.get_feature_importance(), dtype=float)
    if values is None or len(values) != len(features):
        return []
    total = values.sum() or 1.0
    order = np.argsort(values)[::-1][:30]
    return [{"feature": features[int(i)], "importance": float(values[int(i)] / total)} for i in order]


if __name__ == "__main__":
    main()
