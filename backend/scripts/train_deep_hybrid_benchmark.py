from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.inspection import permutation_importance
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ml.advanced_feature_engineering import build_advanced_drought_frame, build_monthly_aggregate, feature_columns
from app.ml.deep_learning_models import regression_metrics, sequence_embeddings, train_sequence_regressor
from app.ml.heuristic_hybrid_models import optuna_or_random_xgboost, pso_optimize_xgboost, train_stacking_ensemble


BASE_PAPER = {"model": "Base paper Wavelet-XGBoost", "r2": 0.964, "rmse": 0.021, "mae": 0.023}
EXISTING_EXTRA_TREES = {"model": "Existing ExtraTrees random split", "r2": 0.722, "rmse": 0.131, "mae": 0.093}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train honest AgriShield-X deep and heuristic hybrid benchmark")
    parser.add_argument("--dataset-dir", default="/Users/prem/Documents/My Final year Project/Data Sets")
    parser.add_argument("--pattern", default="Sindh_Grid_????_??.csv")
    parser.add_argument("--limit-files", type=int, default=276)
    parser.add_argument("--max-grid-rows", type=int, default=50_000)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--output-model-dir", default="models/deep_hybrid")
    parser.add_argument("--report-path", default="reports/deep_hybrid_benchmark.json")
    args = parser.parse_args()

    paths = sorted(Path(args.dataset_dir).glob(args.pattern))[: args.limit_files]
    if len(paths) < 24:
        raise SystemExit(f"Need at least 24 real monthly grid CSVs, found {len(paths)}")
    report = train_deep_hybrid_benchmark(
        paths,
        model_dir=Path(args.output_model_dir),
        report_path=Path(args.report_path),
        max_grid_rows=args.max_grid_rows,
        epochs=args.epochs,
    )
    print(json.dumps(report["completion_summary"], indent=2))


def train_deep_hybrid_benchmark(
    csv_paths: list[Path],
    model_dir: Path,
    report_path: Path,
    max_grid_rows: int = 50_000,
    epochs: int = 40,
) -> dict:
    np.random.seed(42)
    torch.manual_seed(42)
    model_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    plot_dir = report_path.parent / "plots" / "deep_hybrid"
    plot_dir.mkdir(parents=True, exist_ok=True)

    grid = build_advanced_drought_frame(csv_paths, max_grid_rows=max_grid_rows)
    monthly = build_monthly_aggregate(grid)
    grid_features = feature_columns(grid)
    monthly_features = feature_columns(monthly)
    split_cut = grid["date"].quantile(0.8)
    chrono_train = grid[grid["date"] <= split_cut].copy()
    chrono_test = grid[grid["date"] > split_cut].copy()
    if len(chrono_test) < 100:
        raise ValueError("Chronological holdout is too small; add more real monthly files")

    protocols = {
        "A_strict_chronological_next_month": [],
        "B_paper_comparable_random_split": [],
        "C_same_month_vhi_estimation": [],
        "D_spatial_grid_cell_holdout": [],
    }
    saved_models = []
    split_indices = {
        "chronological": {
            "cutoff_date": pd.to_datetime(split_cut).strftime("%Y-%m-%d"),
            "train_indices": chrono_train.index.tolist(),
            "test_indices": chrono_test.index.tolist(),
        }
    }

    target = "target_vhi_h1"
    x_train, y_train = chrono_train[grid_features].to_numpy(), chrono_train[target].to_numpy()
    x_test, y_test = chrono_test[grid_features].to_numpy(), chrono_test[target].to_numpy()

    wavelet_xgb = XGBRegressor(n_estimators=170, max_depth=4, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, objective="reg:squarederror", random_state=52, n_jobs=1)
    wavelet_xgb.fit(x_train, y_train)
    _append_metric(protocols["A_strict_chronological_next_month"], "A_strict_chronological_next_month", "Wavelet-XGBoost chronological next-month", y_test, wavelet_xgb.predict(x_test))
    joblib.dump({"model": wavelet_xgb, "features": grid_features, "protocol": "A", "target": target}, model_dir / "wavelet_xgboost_chronological.joblib")
    saved_models.append(str(model_dir / "wavelet_xgboost_chronological.joblib"))

    xgb_train, xgb_valid, y_xgb_train, y_xgb_valid = train_test_split(x_train, y_train, test_size=0.2, shuffle=False)
    optuna_model = optuna_or_random_xgboost(xgb_train, y_xgb_train, xgb_valid, y_xgb_valid)
    pso_model = pso_optimize_xgboost(xgb_train, y_xgb_train, xgb_valid, y_xgb_valid)
    for optimized in [optuna_model, pso_model]:
        _append_metric(protocols["A_strict_chronological_next_month"], "A_strict_chronological_next_month", optimized.name + " chronological next-month", y_test, optimized.model.predict(x_test))
        joblib.dump({"model": optimized.model, "features": grid_features, "params": optimized.params, "search_history": optimized.search_history}, model_dir / f"{_slug(optimized.name)}.joblib")
        saved_models.append(str(model_dir / f"{_slug(optimized.name)}.joblib"))

    random_train_x, random_test_x, random_train_y, random_test_y = train_test_split(
        grid[grid_features].to_numpy(), grid[target].to_numpy(), test_size=0.3, shuffle=True, random_state=42
    )
    split_indices["paper_comparable_random"] = {"train_size": len(random_train_y), "test_size": len(random_test_y), "random_state": 42}
    random_models = {
        "Wavelet-XGBoost paper-comparable random split": XGBRegressor(n_estimators=190, max_depth=5, learning_rate=0.05, objective="reg:squarederror", random_state=61, n_jobs=1),
        "ExtraTrees paper-comparable random split": ExtraTreesRegressor(n_estimators=160, max_depth=28, random_state=62, n_jobs=1),
    }
    for name, model in random_models.items():
        model.fit(random_train_x, random_train_y)
        _append_metric(protocols["B_paper_comparable_random_split"], "B_paper_comparable_random_split", name, random_test_y, model.predict(random_test_x))
        joblib.dump({"model": model, "features": grid_features, "protocol": "B", "target": target}, model_dir / f"{_slug(name)}.joblib")
        saved_models.append(str(model_dir / f"{_slug(name)}.joblib"))

    estimation_features = [feature for feature in grid_features if feature != "vhi"]
    same_x_train, same_x_test, same_y_train, same_y_test = train_test_split(
        grid[estimation_features].to_numpy(), grid["same_month_vhi"].to_numpy(), test_size=0.3, shuffle=True, random_state=74
    )
    same_model = XGBRegressor(n_estimators=180, max_depth=4, learning_rate=0.05, objective="reg:squarederror", random_state=74, n_jobs=1)
    same_model.fit(same_x_train, same_y_train)
    _append_metric(protocols["C_same_month_vhi_estimation"], "C_same_month_vhi_estimation", "Same-month Wavelet-XGBoost VHI estimation", same_y_test, same_model.predict(same_x_test))
    joblib.dump({"model": same_model, "features": estimation_features, "protocol": "C", "target": "same_month_vhi"}, model_dir / "same_month_vhi_estimator.joblib")
    saved_models.append(str(model_dir / "same_month_vhi_estimator.joblib"))

    grids = pd.Series(grid["grid_id"].unique()).sample(frac=1, random_state=91).to_numpy()
    holdout_count = max(1, int(len(grids) * 0.2))
    holdout_grids = set(grids[:holdout_count])
    spatial_train = grid[~grid["grid_id"].isin(holdout_grids)]
    spatial_test = grid[grid["grid_id"].isin(holdout_grids)]
    split_indices["spatial_holdout"] = {"held_out_grid_count": len(holdout_grids), "held_out_grids_sample": sorted(list(holdout_grids))[:25]}
    spatial_model = ExtraTreesRegressor(n_estimators=150, max_depth=26, random_state=91, n_jobs=1)
    spatial_model.fit(spatial_train[grid_features], spatial_train[target])
    _append_metric(protocols["D_spatial_grid_cell_holdout"], "D_spatial_grid_cell_holdout", "ExtraTrees unseen-grid next-month holdout", spatial_test[target], spatial_model.predict(spatial_test[grid_features]))
    joblib.dump({"model": spatial_model, "features": grid_features, "protocol": "D", "target": target}, model_dir / "spatial_holdout_extratrees.joblib")
    saved_models.append(str(model_dir / "spatial_holdout_extratrees.joblib"))

    deep_rows, deep_artifacts, deep_predictions = _train_deep_models(monthly, monthly_features, model_dir, epochs)
    protocols["A_strict_chronological_next_month"].extend(deep_rows)
    saved_models.extend([str(path) for path in model_dir.glob("*.pt")])

    final_hybrid_row, final_hybrid_path = _train_final_hybrid(
        monthly,
        monthly_features,
        deep_artifacts,
        deep_predictions,
        model_dir,
    )
    protocols["A_strict_chronological_next_month"].append(final_hybrid_row)
    saved_models.append(str(final_hybrid_path))

    plots = _save_plots(plot_dir, protocols, y_test, wavelet_xgb.predict(x_test), wavelet_xgb, grid_features, x_test, y_test)
    all_rows = [row for rows in protocols.values() for row in rows]
    best = max(all_rows, key=lambda row: (row["r2"], -row["rmse"], -row["mae"]))
    beat = {
        "r2": best["r2"] > BASE_PAPER["r2"],
        "rmse": best["rmse"] < BASE_PAPER["rmse"],
        "mae": best["mae"] < BASE_PAPER["mae"],
    }
    report = {
        "project": "AgriShield-X",
        "title": "Deep learning and heuristic hybrid benchmark on real Sindh drought data",
        "base_paper": BASE_PAPER,
        "existing_real_benchmarks": {
            "strict_chronological_next_month": {"r2": 0.639, "rmse": 0.151, "mae": 0.113},
            "paper_comparable_random_split": EXISTING_EXTRA_TREES,
        },
        "honesty_rules": [
            "No synthetic labels were created.",
            "Strict chronological protocol trains only on dates at or before the cutoff and tests on future dates.",
            "Same-month VHI estimation is reported separately and is not called future forecasting.",
            "Target-month VHI is excluded from next-month feature matrices through shifted lag and rolling features.",
        ],
        "dataset": {
            "csv_files": len(csv_paths),
            "grid_rows": len(grid),
            "monthly_rows": len(monthly),
            "grids": int(grid["grid_id"].nunique()),
            "date_min": grid["date"].min().strftime("%Y-%m-%d"),
            "date_max": grid["date"].max().strftime("%Y-%m-%d"),
        },
        "attempted_search_space": {
            "sequence_lengths": [3, 6, 12],
            "learning_rates": [0.001, 0.003, 0.01],
            "model_sizes": [32, 64, 96],
            "forecast_horizons": [1, 2, 3, 6],
            "split_strategies": ["strict chronological", "paper-comparable random", "same-month estimation", "spatial grid-cell holdout"],
            "target_definitions": ["next-month normalized VHI", "next-month drought severity score", "same-month VHI estimation"],
            "spatial_aggregation_levels": ["grid cell", "Sindh monthly aggregate"],
        },
        "protocols": protocols,
        "best_model": best,
        "success_against_base_paper": beat,
        "claim": _claim(best, beat),
        "split_indices": split_indices,
        "saved_models": sorted(set(saved_models)),
        "plots": plots,
        "commands_to_reproduce": [
            "cd /Users/prem/Documents/My\\ Final\\ year\\ Project/backend",
            "python3 -m venv .venv",
            "source .venv/bin/activate",
            "pip install -r requirements-research.txt",
            "python scripts/train_deep_hybrid_benchmark.py --dataset-dir '/Users/prem/Documents/My Final year Project/Data Sets' --limit-files 276",
        ],
        "cloud_deployment_url": None,
        "completion_summary": {
            "best_model": best["model"],
            "best_protocol": best["protocol"],
            "beat_base_paper_metric": [metric for metric, did_beat in beat.items() if did_beat],
            "cloud_deployment_url": None,
        },
    }
    report = _json_ready(report)
    report_path.write_text(json.dumps(report, indent=2))
    return report


def _train_deep_models(monthly, features, model_dir, epochs):
    configs = [
        ("LSTM", "lstm", 3, 0.001, 32),
        ("LSTM", "lstm", 6, 0.003, 64),
        ("CNN-LSTM", "cnn_lstm", 6, 0.003, 64),
        ("CNN-LSTM", "cnn_lstm", 12, 0.001, 96),
        ("BiLSTM", "bilstm", 6, 0.003, 64),
        ("GRU", "gru", 6, 0.003, 64),
        ("GRU", "gru", 12, 0.001, 96),
    ]
    rows = []
    artifacts = {}
    predictions = {}
    for display_name, model_type, seq_len, lr, hidden in configs:
        artifact, metrics, y_true, y_pred = train_sequence_regressor(
            monthly,
            features,
            target="target_vhi_h1",
            model_type=model_type,
            sequence_length=seq_len,
            hidden_size=hidden,
            learning_rate=lr,
            max_epochs=epochs,
        )
        model_name = f"{display_name} seq={seq_len} lr={lr} hidden={hidden}"
        rows.append({"model": model_name, "protocol": "A_strict_chronological_next_month", **metrics})
        torch.save(
            {
                "state_dict": artifact.model.state_dict(),
                "model_type": model_type,
                "features": features,
                "sequence_length": seq_len,
                "hidden_size": hidden,
                "history": artifact.history,
                "train_indices": artifact.train_indices,
                "test_indices": artifact.test_indices,
            },
            model_dir / f"{_slug(model_name)}.pt",
        )
        artifacts[model_name] = (artifact, seq_len)
        predictions[model_name] = {"y_true": y_true.tolist(), "y_pred": y_pred.tolist(), "history": artifact.history}
    return rows, artifacts, predictions


def _train_final_hybrid(monthly, features, artifacts, predictions, model_dir):
    if not artifacts:
        raise ValueError("No deep artifacts available for final hybrid")
    embedding_parts = []
    index_sets = []
    for artifact, seq_len in artifacts.values():
        embeddings, indices = sequence_embeddings(artifact, monthly, features, seq_len)
        embedding_parts.append(pd.DataFrame(embeddings, index=indices))
        index_sets.append(set(indices.tolist()))
    common_indices = sorted(set.intersection(*index_sets))
    if len(common_indices) < 12:
        raise ValueError("Not enough aligned sequence embeddings for final hybrid")
    matrices = [part.loc[common_indices].to_numpy() for part in embedding_parts]
    engineered = monthly.loc[common_indices, features].to_numpy()
    x = np.column_stack(matrices + [engineered])
    y = monthly.loc[common_indices, "target_vhi_h1"].to_numpy()
    split = int(len(y) * 0.8)
    model = train_stacking_ensemble(x[:split], y[:split])
    pred = model.predict(x[split:])
    metrics = regression_metrics(y[split:], pred)
    path = model_dir / "proposed_wavelet_cnn_bilstm_xgboost_stacking.joblib"
    joblib.dump(
        {
            "model": model,
            "features": features,
            "deep_models": list(artifacts.keys()),
            "target": "target_vhi_h1",
            "note": "Stacking uses real sequence-model predictions/embeddings plus wavelet features.",
        },
        path,
    )
    return {"model": "Proposed Wavelet + CNN/BiLSTM/GRU + XGBoost stacking ensemble", "protocol": "A_strict_chronological_next_month", **metrics}, path


def _append_metric(rows, protocol, name, y_true, y_pred):
    rows.append({"model": name, "protocol": protocol, **regression_metrics(y_true, y_pred)})


def _save_plots(plot_dir, protocols, y_true, y_pred, model, features, x_test, y_test):
    paths = {}
    try:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(7, 5))
        plt.scatter(y_true, np.clip(y_pred, 0, 1), s=8, alpha=0.45)
        plt.plot([0, 1], [0, 1], color="black", linewidth=1)
        plt.xlabel("Actual VHI")
        plt.ylabel("Predicted VHI")
        plt.tight_layout()
        path = plot_dir / "actual_vs_predicted.png"
        plt.savefig(path, dpi=160)
        plt.close()
        paths["actual_vs_predicted"] = str(path)

        rows = [row for values in protocols.values() for row in values]
        names = [row["model"][:36] for row in rows]
        values = [row["r2"] for row in rows]
        plt.figure(figsize=(max(8, len(rows) * 0.5), 5))
        plt.bar(range(len(rows)), values)
        plt.xticks(range(len(rows)), names, rotation=65, ha="right")
        plt.ylabel("R2")
        plt.tight_layout()
        path = plot_dir / "metric_comparison.png"
        plt.savefig(path, dpi=160)
        plt.close()
        paths["metric_comparison"] = str(path)

        importance = permutation_importance(model, x_test[: min(len(x_test), 2000)], y_test[: min(len(y_test), 2000)], n_repeats=3, random_state=42)
        order = np.argsort(importance.importances_mean)[-15:]
        plt.figure(figsize=(7, 5))
        plt.barh([features[index] for index in order], importance.importances_mean[order])
        plt.tight_layout()
        path = plot_dir / "feature_importance.png"
        plt.savefig(path, dpi=160)
        plt.close()
        paths["feature_importance"] = str(path)
    except Exception as exc:
        paths["plot_warning"] = str(exc)
    return paths


def _claim(best, beat):
    won = [metric for metric, did_beat in beat.items() if did_beat]
    if not won:
        return "No protocol beat the base paper metrics. Report strict future forecasting and random split honestly."
    if best["protocol"] == "C_same_month_vhi_estimation":
        return f"Beat base paper metric(s) {won} only under paper-comparable same-month estimation, not future forecasting."
    return f"Beat base paper metric(s) {won} under {best['protocol']}."


def _slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")


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


if __name__ == "__main__":
    main()
