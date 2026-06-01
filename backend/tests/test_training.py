from pathlib import Path

import joblib

from app.ml.train import train_from_csv
from scripts.etl_sources import generate_sample_dataset


def test_train_from_csv_saves_best_model(tmp_path):
    csv_path = tmp_path / "sample.csv"
    model_path = tmp_path / "best_model.joblib"
    report_path = tmp_path / "model_metrics.json"
    generate_sample_dataset(csv_path, months=30)

    report = train_from_csv(csv_path, model_path, report_path)
    artifact = joblib.load(model_path)

    assert model_path.exists()
    assert report_path.exists()
    assert report["best_model"] in {"linear_regression", "random_forest", "xgboost"}
    assert artifact["features"]

