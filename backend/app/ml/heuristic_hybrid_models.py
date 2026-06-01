from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor, StackingRegressor
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from app.ml.deep_learning_models import regression_metrics


@dataclass
class OptimizedModel:
    name: str
    model: object
    params: dict
    search_history: list[dict]


def optuna_or_random_xgboost(x_train, y_train, x_valid, y_valid, n_trials: int = 12) -> OptimizedModel:
    history = []
    try:
        import optuna

        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 80, 260),
                "max_depth": trial.suggest_int("max_depth", 2, 7),
                "learning_rate": trial.suggest_float("learning_rate", 0.015, 0.14, log=True),
                "subsample": trial.suggest_float("subsample", 0.65, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.65, 1.0),
                "min_child_weight": trial.suggest_float("min_child_weight", 1.0, 8.0),
            }
            model = _xgb(params)
            model.fit(x_train, y_train)
            pred = model.predict(x_valid)
            score = regression_metrics(y_valid, pred)["rmse"]
            history.append({"trial": len(history), "rmse": score, "params": params})
            return score

        study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
        best_params = study.best_params
        name = "Optuna-optimized Wavelet XGBoost"
    except Exception:
        rng = np.random.default_rng(42)
        best_params = None
        best_score = math.inf
        for trial in range(n_trials):
            params = {
                "n_estimators": int(rng.integers(80, 240)),
                "max_depth": int(rng.integers(2, 7)),
                "learning_rate": float(10 ** rng.uniform(np.log10(0.015), np.log10(0.14))),
                "subsample": float(rng.uniform(0.65, 1.0)),
                "colsample_bytree": float(rng.uniform(0.65, 1.0)),
                "min_child_weight": float(rng.uniform(1.0, 8.0)),
            }
            model = _xgb(params)
            model.fit(x_train, y_train)
            score = regression_metrics(y_valid, model.predict(x_valid))["rmse"]
            history.append({"trial": trial, "rmse": score, "params": params})
            if score < best_score:
                best_score = score
                best_params = params
        name = "Random-search Wavelet XGBoost fallback"
    model = _xgb(best_params)
    model.fit(np.vstack([x_train, x_valid]), np.concatenate([y_train, y_valid]))
    return OptimizedModel(name=name, model=model, params=best_params, search_history=history)


def pso_optimize_xgboost(x_train, y_train, x_valid, y_valid, particles: int = 6, iterations: int = 5) -> OptimizedModel:
    rng = np.random.default_rng(7)
    bounds = np.asarray(
        [
            [80, 260],
            [2, 7],
            [0.015, 0.14],
            [0.65, 1.0],
            [0.65, 1.0],
        ],
        dtype=float,
    )
    positions = bounds[:, 0] + rng.random((particles, bounds.shape[0])) * (bounds[:, 1] - bounds[:, 0])
    velocities = rng.normal(0, 0.1, positions.shape)
    personal_best = positions.copy()
    personal_scores = np.full(particles, math.inf)
    global_best = positions[0].copy()
    global_score = math.inf
    history = []
    for iteration in range(iterations):
        for index in range(particles):
            params = _params_from_position(positions[index])
            model = _xgb(params)
            model.fit(x_train, y_train)
            score = regression_metrics(y_valid, model.predict(x_valid))["rmse"]
            history.append({"iteration": iteration, "particle": index, "rmse": score, "params": params})
            if score < personal_scores[index]:
                personal_scores[index] = score
                personal_best[index] = positions[index].copy()
            if score < global_score:
                global_score = score
                global_best = positions[index].copy()
        inertia = 0.55
        cognitive = 1.25 * rng.random(positions.shape) * (personal_best - positions)
        social = 1.25 * rng.random(positions.shape) * (global_best - positions)
        velocities = inertia * velocities + cognitive + social
        positions = np.clip(positions + velocities, bounds[:, 0], bounds[:, 1])
    best_params = _params_from_position(global_best)
    model = _xgb(best_params)
    model.fit(np.vstack([x_train, x_valid]), np.concatenate([y_train, y_valid]))
    return OptimizedModel(name="PSO-optimized Wavelet XGBoost", model=model, params=best_params, search_history=history)


def train_stacking_ensemble(x_train, y_train) -> StackingRegressor:
    estimators = [
        ("xgb", _xgb({"n_estimators": 180, "max_depth": 4, "learning_rate": 0.05, "subsample": 0.9, "colsample_bytree": 0.9})),
        ("extra_trees", ExtraTreesRegressor(n_estimators=140, max_depth=26, random_state=43, n_jobs=1)),
    ]
    final_estimator = XGBRegressor(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.04,
        objective="reg:squarederror",
        random_state=91,
        n_jobs=1,
    )
    model = StackingRegressor(estimators=estimators, final_estimator=final_estimator, passthrough=True, n_jobs=1)
    model.fit(x_train, y_train)
    return model


def random_split(x, y, test_size: float = 0.3):
    return train_test_split(x, y, test_size=test_size, shuffle=True, random_state=42)


def _xgb(params: dict) -> XGBRegressor:
    safe = dict(params)
    safe["n_estimators"] = int(safe.get("n_estimators", 160))
    safe["max_depth"] = int(safe.get("max_depth", 4))
    safe.setdefault("objective", "reg:squarederror")
    safe.setdefault("random_state", 42)
    safe.setdefault("n_jobs", 1)
    return XGBRegressor(**safe)


def _params_from_position(position: np.ndarray) -> dict:
    return {
        "n_estimators": int(position[0]),
        "max_depth": int(position[1]),
        "learning_rate": float(position[2]),
        "subsample": float(position[3]),
        "colsample_bytree": float(position[4]),
    }
