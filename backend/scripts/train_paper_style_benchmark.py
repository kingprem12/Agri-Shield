from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ml.paper_style_benchmark import train_paper_style_benchmark


DEFAULT_DATASET_DIR = Path("/Users/prem/Documents/My Final year Project/Data Sets")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train paper-style normalized VHI benchmark")
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--pattern", default="Sindh_Grid_????_??.csv")
    parser.add_argument("--limit-files", type=int, default=276)
    args = parser.parse_args()
    paths = sorted(Path(args.dataset_dir).glob(args.pattern))[: args.limit_files]
    report = train_paper_style_benchmark(
        csv_paths=paths,
        model_path=Path("models/research/paper_style_vhi_estimator.joblib"),
        report_path=Path("reports/paper_style_benchmark.json"),
    )
    print(report)


if __name__ == "__main__":
    main()

