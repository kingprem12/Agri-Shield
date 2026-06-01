from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ml.x_train import train_agrishield_x


DEFAULT_DATASET_DIR = Path("/Users/prem/Documents/My Final year Project/Data Sets")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train AgriShield-X VHI forecasting models")
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--pattern", default="Sindh_Grid_20*.csv")
    parser.add_argument("--limit-files", type=int, default=36)
    args = parser.parse_args()
    paths = sorted(Path(args.dataset_dir).glob(args.pattern))[: args.limit_files]
    if not paths:
        raise SystemExit(f"No CSV files found in {args.dataset_dir} matching {args.pattern}")
    report = train_agrishield_x(
        csv_paths=paths,
        model_path=Path("models/agrishield_x_vhi_forecaster.joblib"),
        report_path=Path("reports/agrishield_x_benchmark.json"),
    )
    print(report)


if __name__ == "__main__":
    main()

