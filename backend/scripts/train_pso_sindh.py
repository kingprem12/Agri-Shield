from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ml.pso_sindh import train_pso_sindh_model

BACKEND_DIR = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Train PSO-Optimized Wavelet-XGBoost for Sindh drought prediction")
    parser.add_argument("--dataset-dir", default="/Users/prem/Documents/My Final year Project/Data Sets")
    parser.add_argument("--pattern", default="Sindh_Grid_*.csv")
    parser.add_argument("--limit-files", type=int, default=276)
    parser.add_argument("--max-grid-rows", type=int, default=50000)
    parser.add_argument("--particles", type=int, default=8)
    parser.add_argument("--iterations", type=int, default=7)
    parser.add_argument("--model-path", default=str(BACKEND_DIR / "models" / "pso_sindh" / "pso_wavelet_xgboost_sindh.joblib"))
    parser.add_argument("--report-path", default=str(BACKEND_DIR / "reports" / "pso_sindh_metrics.json"))
    args = parser.parse_args()

    report = train_pso_sindh_model(
        dataset_dir=Path(args.dataset_dir),
        pattern=args.pattern,
        limit_files=args.limit_files,
        max_grid_rows=args.max_grid_rows,
        particles=args.particles,
        iterations=args.iterations,
        model_path=Path(args.model_path),
        report_path=Path(args.report_path),
    )
    print(json.dumps({"best_model": report["best_model"], "claim": report["claim"]}, indent=2))


if __name__ == "__main__":
    main()
