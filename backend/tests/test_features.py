import pandas as pd

from app.ml.features import MODEL_FEATURES, prepare_training_frame
from scripts.etl_sources import generate_sample_dataset


def test_prepare_training_frame_adds_expected_features(tmp_path):
    csv_path = tmp_path / "sample.csv"
    raw = generate_sample_dataset(csv_path, months=24)
    frame = prepare_training_frame(raw)

    assert not frame[MODEL_FEATURES].isna().any().any()
    assert "risk_score" in frame.columns
    assert frame["risk_score"].between(0, 100).all()

