from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.pso_future import train_pso_future_forecaster


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train strict future PSO Wavelet-Lag ExtraTrees + XGBoost ensemble.")
    parser.add_argument("--dataset-dir", default="/Users/prem/Documents/My Final year Project/Data Sets")
    parser.add_argument("--dataset-csv", default="/Users/prem/Documents/My Final year Project/backend/data/processed/sindh_gee_expanded_training.csv")
    parser.add_argument("--pattern", default="Sindh_Grid_*.csv")
    parser.add_argument("--limit-files", type=int, default=276)
    parser.add_argument("--max-grid-rows", type=int, default=30000)
    parser.add_argument("--particles", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--seed", type=int, default=29)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = train_pso_future_forecaster(
        dataset_dir=Path(args.dataset_dir),
        pattern=args.pattern,
        limit_files=args.limit_files,
        max_grid_rows=args.max_grid_rows,
        particles=args.particles,
        iterations=args.iterations,
        seed=args.seed,
        dataset_csv=Path(args.dataset_csv) if args.dataset_csv else None,
    )
    print(json.dumps(report["protocols"], indent=2))
    print(report["claim"])


if __name__ == "__main__":
    main()
