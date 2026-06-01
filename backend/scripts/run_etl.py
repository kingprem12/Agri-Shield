from __future__ import annotations

import argparse
from pathlib import Path

from etl_sources import generate_sample_dataset, modis_appeears_note


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AgriShield ETL")
    parser.add_argument("--sample", action="store_true", help="Use offline reproducible sample data")
    parser.add_argument("--output", default="data/processed/agri_monthly_features.csv")
    args = parser.parse_args()

    output = Path(args.output)
    if args.sample:
        generate_sample_dataset(output)
        print(f"Sample ETL complete: {output}")
        return

    raise SystemExit(
        "Live ETL requires NASA Earthdata/AppEEARS credentials and CHIRPS raster processing. "
        f"{modis_appeears_note()} Use --sample for localhost validation."
    )


if __name__ == "__main__":
    main()

