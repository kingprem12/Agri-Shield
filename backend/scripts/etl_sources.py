from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests


INDIA_DISTRICTS = [
    ("Maharashtra", "Pune", 18.5204, 73.8567),
    ("Karnataka", "Bengaluru Rural", 13.2847, 77.6078),
    ("Rajasthan", "Jodhpur", 26.2389, 73.0243),
    ("Punjab", "Ludhiana", 30.9010, 75.8573),
    ("Tamil Nadu", "Coimbatore", 11.0168, 76.9558),
]


def nasa_power_monthly(latitude: float, longitude: float, start: str, end: str) -> pd.DataFrame:
    url = "https://power.larc.nasa.gov/api/temporal/monthly/point"
    params = {
        "parameters": "T2M,RH2M,WS2M",
        "community": "AG",
        "longitude": longitude,
        "latitude": latitude,
        "start": start[:4],
        "end": end[:4],
        "format": "JSON",
    }
    response = requests.get(url, params=params, timeout=45)
    response.raise_for_status()
    values = response.json()["properties"]["parameter"]
    rows = []
    for key, temp in values["T2M"].items():
        if key.endswith("13"):
            continue
        rows.append(
            {
                "date": pd.to_datetime(key, format="%Y%m"),
                "temperature": temp,
                "humidity": values["RH2M"][key],
                "wind_speed": values["WS2M"][key],
            }
        )
    return pd.DataFrame(rows)


def chirps_monthly_url(year: int, month: int) -> str:
    return f"https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs/chirps-v2.0.{year}.{month:02d}.tif.gz"


def modis_appeears_note() -> str:
    return (
        "MODIS NDVI/LST production downloads should be configured through NASA AppEEARS or Earthdata. "
        "Set Earthdata credentials and request MOD13Q1 NDVI plus MOD11A2 LST for your AOI."
    )


def generate_sample_dataset(output_csv: Path, months: int = 72) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range(end=date.today().replace(day=1), periods=months, freq="MS")
    rows = []
    for state, district, latitude, longitude in INDIA_DISTRICTS:
        aridity = 0.15 + (longitude - 68) / 120
        for index, current_date in enumerate(dates):
            seasonal = np.sin(2 * np.pi * (current_date.month - 1) / 12)
            rainfall = max(0, 110 + 95 * seasonal - 75 * aridity + rng.normal(0, 18))
            lst = 28 + 6 * (-seasonal) + 8 * aridity + rng.normal(0, 1.6)
            ndvi = np.clip(0.62 + rainfall / 650 - lst / 120 + rng.normal(0, 0.035), 0.12, 0.88)
            temperature = lst - 2 + rng.normal(0, 1.2)
            humidity = np.clip(45 + rainfall / 5 - aridity * 35 + rng.normal(0, 7), 18, 95)
            wind_speed = np.clip(2.4 + aridity * 2 + rng.normal(0, 0.5), 0.2, 9)
            soil = np.clip(0.25 + rainfall / 330 + ndvi / 3 - aridity / 3 + rng.normal(0, 0.04), 0.05, 0.95)
            rows.append(
                {
                    "date": current_date.date().isoformat(),
                    "state": state,
                    "district": district,
                    "latitude": latitude,
                    "longitude": longitude,
                    "ndvi": ndvi,
                    "lst": lst,
                    "rainfall": rainfall,
                    "temperature": temperature,
                    "humidity": humidity,
                    "wind_speed": wind_speed,
                    "soil_moisture_proxy": soil,
                }
            )
            if index % 19 == 0:
                rows[-1]["ndvi"] = np.nan
    frame = pd.DataFrame(rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_csv, index=False)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description="AgriShield AI ETL source helpers")
    parser.add_argument("--sample", action="store_true", help="Generate deterministic offline sample dataset")
    parser.add_argument("--output", default="data/processed/agri_monthly_features.csv")
    args = parser.parse_args()
    if args.sample:
        frame = generate_sample_dataset(Path(args.output))
        print(f"Generated sample dataset with {len(frame)} rows at {args.output}")
    else:
        print(modis_appeears_note())
        print("Example CHIRPS URL:", chirps_monthly_url(2024, 6))


if __name__ == "__main__":
    main()

