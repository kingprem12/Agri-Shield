from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
from PIL import Image, ImageDraw

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ml.advanced_feature_engineering import build_advanced_drought_frame, feature_columns


def main() -> None:
    dataset_dir = Path("/Users/prem/Documents/My Final year Project/Data Sets")
    paths = sorted(dataset_dir.glob("Sindh_Grid_????_??.csv"))[:276]
    grid = build_advanced_drought_frame(paths, max_grid_rows=10000)
    features = feature_columns(grid)
    cutoff = grid["date"].quantile(0.8)
    test = grid[grid["date"] > cutoff]
    artifact = joblib.load("models/deep_hybrid/wavelet_xgboost_chronological.joblib")
    model = artifact["model"]
    y_true = test["target_vhi_h1"].to_numpy()
    y_pred = np.clip(model.predict(test[features].to_numpy()), 0, 1)

    output_dir = Path("reports/plots/deep_hybrid")
    output_dir.mkdir(parents=True, exist_ok=True)
    plots = {
        "actual_vs_predicted": str(output_dir / "actual_vs_predicted.png"),
        "metric_comparison": str(output_dir / "metric_comparison.png"),
        "feature_importance": str(output_dir / "feature_importance.png"),
    }
    _actual_vs_predicted(Path(plots["actual_vs_predicted"]), y_true, y_pred)
    report = json.loads(Path("reports/deep_hybrid_benchmark.json").read_text())
    rows = [row for values in report["protocols"].values() for row in values]
    _metric_comparison(Path(plots["metric_comparison"]), rows)
    _feature_importance(Path(plots["feature_importance"]), model, features)
    report["plots"] = plots
    Path("reports/deep_hybrid_benchmark.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(plots, indent=2))


def _canvas(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (width, height), (255, 255, 255))
    return image, ImageDraw.Draw(image)


def _actual_vs_predicted(path: Path, y_true: np.ndarray, y_pred: np.ndarray) -> None:
    image, draw = _canvas(900, 650)
    ink = (15, 23, 42)
    blue = (79, 70, 229)
    draw.text((30, 20), "Actual vs Predicted VHI", fill=ink)
    draw.rectangle((80, 70, 840, 590), outline=(203, 213, 225))
    draw.line((80, 590, 840, 70), fill=(100, 116, 139), width=2)
    step = max(1, len(y_true) // 1800)
    for actual, predicted in zip(y_true[::step], y_pred[::step]):
        x_pos = 80 + float(actual) * 760
        y_pos = 590 - float(predicted) * 520
        draw.ellipse((x_pos - 2, y_pos - 2, x_pos + 2, y_pos + 2), fill=blue)
    image.save(path)


def _metric_comparison(path: Path, rows: list[dict]) -> None:
    image, draw = _canvas(1200, 700)
    ink = (15, 23, 42)
    green = (16, 185, 129)
    blue = (79, 70, 229)
    draw.text((30, 20), "Metric Comparison: R2 by Model", fill=ink)
    max_value = max(1.0, max(row["r2"] for row in rows))
    bar_width = max(12, 1050 // len(rows))
    baseline = 620
    for index, row in enumerate(rows):
        height = max(0, int((row["r2"] / max_value) * 520))
        x_pos = 80 + index * bar_width
        color = green if row["protocol"].startswith("C") else blue
        draw.rectangle((x_pos, baseline - height, x_pos + bar_width - 4, baseline), fill=color)
        draw.text((x_pos, baseline + 8), str(index + 1), fill=ink)
    draw.text((30, 650), "Models numbered in report order; green marks same-month estimation.", fill=ink)
    image.save(path)


def _feature_importance(path: Path, model, features: list[str]) -> None:
    image, draw = _canvas(1000, 650)
    ink = (15, 23, 42)
    green = (16, 185, 129)
    importances = getattr(model, "feature_importances_", np.zeros(len(features)))
    order = np.argsort(importances)[-15:]
    max_importance = max(float(importances[order].max()), 1e-9)
    draw.text((30, 20), "Feature Importance: Chronological Wavelet-XGBoost", fill=ink)
    for row_number, feature_index in enumerate(order):
        y_pos = 70 + row_number * 36
        width = int(float(importances[feature_index]) / max_importance * 620)
        draw.text((30, y_pos), features[feature_index][:38], fill=ink)
        draw.rectangle((360, y_pos, 360 + width, y_pos + 22), fill=green)
        draw.text((370 + width, y_pos), f"{float(importances[feature_index]):.3f}", fill=ink)
    image.save(path)


if __name__ == "__main__":
    main()
