from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ml.deep_research import train_three_research_models


DEFAULT_DATASET_DIR = Path("/Users/prem/Documents/My Final year Project/Data Sets")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train real AgriShield-X LSTM, CNN and Hybrid models")
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--pattern", default="Sindh_Grid_????_??.csv")
    parser.add_argument("--limit-files", type=int, default=276)
    args = parser.parse_args()
    paths = sorted(Path(args.dataset_dir).glob(args.pattern))[: args.limit_files]
    if len(paths) < 24:
        raise SystemExit(f"Need at least 24 monthly grid CSVs, found {len(paths)}")
    report = train_three_research_models(
        csv_paths=paths,
        output_dir=Path("models/research"),
        report_path=Path("reports/deep_research_metrics.json"),
    )
    print(report)


if __name__ == "__main__":
    main()

