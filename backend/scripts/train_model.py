from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ml.train import train_from_csv


def main() -> None:
    report = train_from_csv(
        input_csv=Path("data/processed/agri_monthly_features.csv"),
        model_path=Path("models/best_model.joblib"),
        report_path=Path("reports/model_metrics.json"),
    )
    print(report)


if __name__ == "__main__":
    main()
