from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ml.gridcell_forecast_benchmark import train_gridcell_forecast_benchmark


DEFAULT_DATASET_DIR = Path("/Users/prem/Documents/My Final year Project/Data Sets")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train real grid-cell next-month VHI benchmark")
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--pattern", default="Sindh_Grid_????_??.csv")
    parser.add_argument("--limit-files", type=int, default=276)
    parser.add_argument("--max-rows", type=int, default=250000)
    args = parser.parse_args()
    paths = sorted(Path(args.dataset_dir).glob(args.pattern))[: args.limit_files]
    report = train_gridcell_forecast_benchmark(
        csv_paths=paths,
        model_path=Path("models/research/gridcell_next_month_vhi_stack.joblib"),
        report_path=Path("reports/gridcell_forecast_benchmark.json"),
        max_rows=args.max_rows,
    )
    print(report)


if __name__ == "__main__":
    main()
