from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DATASET_DIR = Path("/Users/prem/Documents/My Final year Project/Data Sets")
OUTPUT_PATH = Path("data/processed/sindh_gee_expanded_training.csv")
REPORT_PATH = Path("reports/sindh_gee_expansion_report.json")
EXPORT_DIR = Path("data/raw/gee_sindh_exports")
FILL_VALUE = -9999.0
EXPORT_COLUMNS = [
    "grid_id",
    "longitude",
    "latitude",
    "date",
    "year",
    "month",
    "soil_moisture",
    "temperature",
    "humidity",
    "evapotranspiration",
    "wind_speed",
    "solar_radiation",
    "evi",
    "modis_ndvi",
    "modis_lst",
    "chirps_rainfall",
    "mndwi",
    "has_smap",
    "has_era5",
    "has_sentinel2",
    "has_modis",
    "has_chirps",
]

GEE_COLLECTIONS = {
    "smap_soil_moisture": "NASA_USDA/HSL/SMAP10KM_soil_moisture",
    "era5_land": "ECMWF/ERA5_LAND/MONTHLY_AGGR",
    "modis_ndvi_evi": "MODIS/061/MOD13Q1",
    "modis_lst": "MODIS/061/MOD11A2",
    "chirps_rainfall": "UCSB-CHG/CHIRPS/DAILY",
    "sentinel2_mndwi": "COPERNICUS/S2_SR_HARMONIZED",
}

NEW_VARIABLES = [
    "soil_moisture",
    "temperature",
    "humidity",
    "evapotranspiration",
    "wind_speed",
    "solar_radiation",
    "evi",
    "mndwi",
    "rainfall_anomaly",
    "spi_1",
    "spi_3",
    "spi_6",
    "spi_12",
    "spei_1",
    "spei_3",
    "spei_6",
    "spei_12",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expand Sindh grid dataset with monthly GEE climate/remote-sensing features.")
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--export-dir", type=Path, default=EXPORT_DIR)
    parser.add_argument("--mode", choices=["profile", "gee-export", "merge-exports", "validate-exports", "list-broken-months"], default="profile")
    parser.add_argument("--limit-months", type=int, default=None, help="Optional small-run limit for export task creation.")
    parser.add_argument("--months", default=None, help="Comma-separated YYYY-MM months to export, e.g. 2022-09,2022-10.")
    parser.add_argument("--start-month", default=None, help="Optional first month to export, YYYY-MM.")
    parser.add_argument("--end-month", default=None, help="Optional last month to export, YYYY-MM.")
    parser.add_argument("--max-null-pct", type=float, default=90.0, help="Broken-month threshold for GEE feature null percentage.")
    parser.add_argument("--drive-folder", default="agrishield_sindh_gee_exports")
    parser.add_argument("--scale", type=int, default=10000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base = load_existing_sindh(args.dataset_dir)
    if args.mode == "profile":
        write_profile(base, args.output, args.report)
        return
    if args.mode == "merge-exports":
        expanded = merge_exported_features(base, args.export_dir)
        expanded = add_climate_indices(expanded)
        write_outputs(expanded, args.output, args.report, status="merged_from_downloaded_gee_exports")
        return
    if args.mode == "validate-exports":
        print(json.dumps(validate_exports(base, args.export_dir, args.max_null_pct), indent=2))
        return
    if args.mode == "list-broken-months":
        report = validate_exports(base, args.export_dir, args.max_null_pct)
        print(json.dumps(build_broken_month_report(report), indent=2))
        return
    create_gee_export_tasks(base, args.drive_folder, args.limit_months, args.scale, args.months, args.start_month, args.end_month)


def load_existing_sindh(dataset_dir: Path) -> pd.DataFrame:
    paths = sorted(dataset_dir.glob("Sindh_Grid_*.csv"))
    if not paths:
        raise FileNotFoundError(f"No Sindh_Grid_*.csv files found in {dataset_dir}")
    frames = []
    for path in paths:
        frame = pd.read_csv(path)
        frame["source_file"] = path.name
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    data = data.rename(columns={"system:index": "grid_id", "NDVI": "ndvi", "LST": "lst", "Precipitation": "precipitation"})
    coords = data[".geo"].apply(parse_geo)
    data["longitude"] = coords.apply(lambda item: item[0])
    data["latitude"] = coords.apply(lambda item: item[1])
    data["date"] = pd.to_datetime(data["date"].astype(str).str.replace("_", "-", regex=False) + "-01", errors="coerce")
    data["grid_id"] = data["grid_id"].astype(str)
    columns = ["grid_id", "date", "year", "month", "longitude", "latitude", "ndvi", "lst", "precipitation", "source_file"]
    return data[columns].dropna(subset=["grid_id", "date", "longitude", "latitude"]).sort_values(["grid_id", "date"]).reset_index(drop=True)


def parse_geo(value: Any) -> tuple[float, float]:
    geo = json.loads(str(value))
    lon, lat = geo.get("coordinates", [np.nan, np.nan])
    return float(lon), float(lat)


def write_profile(base: pd.DataFrame, output_path: Path, report_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    base.to_csv(output_path, index=False)
    report = build_report(
        base,
        status="profile_only_gee_not_collected",
        note=(
            "Local grid/date template verified. Install/authenticate earthengine-api, run gee-export, "
            "download exports, then run merge-exports to create the fully enriched training dataset."
        ),
    )
    report_path.write_text(json.dumps(report, indent=2))
    print(json.dumps({"merged_dataset_path": str(output_path), "report_path": str(report_path), "status": report["status"]}, indent=2))


def create_gee_export_tasks(
    base: pd.DataFrame,
    drive_folder: str,
    limit_months: int | None,
    scale: int,
    months: str | None = None,
    start_month: str | None = None,
    end_month: str | None = None,
) -> None:
    try:
        import ee
    except ImportError as exc:
        raise RuntimeError("earthengine-api is not installed. Run: pip install earthengine-api") from exc
    try:
        ee.Initialize()
    except Exception as exc:
        raise RuntimeError("Google Earth Engine is not authenticated. Run: earthengine authenticate") from exc

    dates = select_export_dates(base, months, start_month, end_month)
    if limit_months:
        dates = dates[:limit_months]
    grid = base[["grid_id", "longitude", "latitude"]].drop_duplicates("grid_id")
    features = [
        ee.Feature(ee.Geometry.Point([row.longitude, row.latitude]), {"grid_id": row.grid_id, "longitude": row.longitude, "latitude": row.latitude})
        for row in grid.itertuples(index=False)
    ]
    points = ee.FeatureCollection(features)
    tasks = []
    for date in dates:
        start = pd.Timestamp(date)
        end = start + pd.DateOffset(months=1)
        image = build_monthly_gee_image(ee, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        sampled = image.sampleRegions(collection=points, scale=scale, geometries=False).map(
            lambda feature: feature.set({"date": start.strftime("%Y-%m-%d"), "year": start.year, "month": start.month})
        )
        description = f"agrishield_sindh_gee_{start.year}_{start.month:02d}"
        task = ee.batch.Export.table.toDrive(
            collection=sampled,
            description=description,
            folder=drive_folder,
            fileNamePrefix=description,
            fileFormat="CSV",
            selectors=EXPORT_COLUMNS,
        )
        task.start()
        task_info = {"description": description, "date": start.strftime("%Y-%m-%d")}
        tasks.append(task_info)
        print(json.dumps({"started_task": task_info}), flush=True)
    print(json.dumps({"started_tasks": len(tasks), "drive_folder": drive_folder, "tasks": tasks[:10]}, indent=2))


def select_export_dates(base: pd.DataFrame, months: str | None, start_month: str | None, end_month: str | None) -> list[pd.Timestamp]:
    dates = [pd.Timestamp(date) for date in sorted(base["date"].dropna().unique())]
    if months:
        requested = {pd.Period(item.strip(), freq="M") for item in months.split(",") if item.strip()}
        dates = [date for date in dates if pd.Period(date, freq="M") in requested]
    if start_month:
        start = pd.Period(start_month, freq="M")
        dates = [date for date in dates if pd.Period(date, freq="M") >= start]
    if end_month:
        end = pd.Period(end_month, freq="M")
        dates = [date for date in dates if pd.Period(date, freq="M") <= end]
    return dates


def build_monthly_gee_image(ee, start: str, end: str):
    smap_collection = ee.ImageCollection(GEE_COLLECTIONS["smap_soil_moisture"]).filterDate(start, end)
    era5_collection = ee.ImageCollection(GEE_COLLECTIONS["era5_land"]).filterDate(start, end)
    mod13_collection = ee.ImageCollection(GEE_COLLECTIONS["modis_ndvi_evi"]).filterDate(start, end)
    mod11_collection = ee.ImageCollection(GEE_COLLECTIONS["modis_lst"]).filterDate(start, end)
    chirps_collection = ee.ImageCollection(GEE_COLLECTIONS["chirps_rainfall"]).filterDate(start, end)
    s2_collection = ee.ImageCollection(GEE_COLLECTIONS["sentinel2_mndwi"]).filterDate(start, end).filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 45))

    smap = smap_collection.mean()
    era5 = era5_collection.mean()
    mod13 = mod13_collection.mean()
    mod11 = mod11_collection.mean()
    chirps = chirps_collection.sum()

    soil = first_existing_band(ee, smap, ["ssm", "susm", "ssma", "susma"], "soil_moisture")
    temp = first_existing_band(ee, era5, ["temperature_2m"], "temperature").subtract(273.15)
    dew = first_existing_band(ee, era5, ["dewpoint_temperature_2m"], "dewpoint_temperature").subtract(273.15)
    humidity = relative_humidity(ee, temp, dew).rename("humidity")
    evap = first_existing_band(ee, era5, ["total_evaporation_sum", "evaporation_from_vegetation_transpiration_sum"], "evapotranspiration").abs()
    u_wind = first_existing_band(ee, era5, ["u_component_of_wind_10m"], "u_wind")
    v_wind = first_existing_band(ee, era5, ["v_component_of_wind_10m"], "v_wind")
    wind = u_wind.pow(2).add(v_wind.pow(2)).sqrt().rename("wind_speed")
    solar = first_existing_band(ee, era5, ["surface_solar_radiation_downwards_sum"], "solar_radiation")
    evi = first_existing_band(ee, mod13, ["EVI"], "evi").multiply(0.0001)
    modis_ndvi = first_existing_band(ee, mod13, ["NDVI"], "modis_ndvi").multiply(0.0001)
    modis_lst = first_existing_band(ee, mod11, ["LST_Day_1km"], "modis_lst").multiply(0.02).subtract(273.15)
    rainfall = first_existing_band(ee, chirps, ["precipitation"], "chirps_rainfall")
    mndwi = safe_mndwi(ee, s2_collection)
    flags = [
        availability_flag(ee, smap_collection, "has_smap"),
        availability_flag(ee, era5_collection, "has_era5"),
        availability_flag(ee, s2_collection, "has_sentinel2"),
        availability_flag(ee, mod13_collection.merge(mod11_collection), "has_modis"),
        availability_flag(ee, chirps_collection, "has_chirps"),
    ]
    image = ee.Image.cat([soil, temp, humidity, evap, wind, solar, evi, modis_ndvi, modis_lst, rainfall, mndwi] + flags).toFloat()
    return image.unmask(FILL_VALUE)


def first_existing_band(ee, image, candidates: list[str], output_name: str):
    empty = ee.Image.constant(FILL_VALUE).rename(output_name)

    def choose(band, current):
        band = ee.String(band)
        current = ee.Image(current)
        return ee.Algorithms.If(image.bandNames().contains(band), image.select([band]).rename(output_name).unmask(FILL_VALUE), current)

    return ee.Image(ee.List(candidates).iterate(choose, empty))


def safe_mndwi(ee, collection):
    empty = ee.Image.constant(FILL_VALUE).rename("mndwi")
    image = ee.Image(collection.median())
    has_b3 = image.bandNames().contains("B3")
    has_b11 = image.bandNames().contains("B11")
    return ee.Image(ee.Algorithms.If(has_b3, ee.Algorithms.If(has_b11, image.normalizedDifference(["B3", "B11"]).rename("mndwi").unmask(FILL_VALUE), empty), empty))


def availability_flag(ee, collection, output_name: str):
    return ee.Image.constant(collection.size().gt(0)).rename(output_name).toFloat()


def relative_humidity(ee, temp_c, dew_c):
    numerator = dew_c.multiply(17.625).divide(dew_c.add(243.04)).exp()
    denominator = temp_c.multiply(17.625).divide(temp_c.add(243.04)).exp()
    return numerator.divide(denominator).multiply(100).clamp(0, 100)


def merge_exported_features(base: pd.DataFrame, export_dir: Path) -> pd.DataFrame:
    paths = sorted(export_dir.glob("*.csv"))
    if not paths:
        raise FileNotFoundError(f"No downloaded GEE export CSV files found in {export_dir}")
    frames = []
    skipped = []
    for path in paths:
        try:
            frame = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            skipped.append(path.name)
            continue
        if frame.empty or not {"grid_id", "date"}.issubset(frame.columns):
            skipped.append(path.name)
            continue
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["grid_id"] = frame["grid_id"].astype(str)
        frame = frame.replace(FILL_VALUE, np.nan)
        frame = frame.replace({value: np.nan for value in [-9999, -9999.0, -10272.15]})
        frames.append(frame)
    if not frames:
        raise ValueError(f"No readable non-empty GEE export CSV files found in {export_dir}")
    if skipped:
        print(json.dumps({"skipped_empty_or_invalid_exports": len(skipped), "examples": skipped[:20]}, indent=2))
    gee = pd.concat(frames, ignore_index=True)
    gee = gee.groupby(["grid_id", "date"], as_index=False).mean(numeric_only=True)
    base = collapse_grid_date_rows(base)
    merged = base.merge(gee, on=["grid_id", "date"], how="left", suffixes=("", "_gee"))
    merged = collapse_grid_date_rows(merged)
    merged = add_vhi_targets(merged)
    return merged.sort_values(["grid_id", "date"]).reset_index(drop=True)


def collapse_grid_date_rows(data: pd.DataFrame) -> pd.DataFrame:
    if not {"grid_id", "date"}.issubset(data.columns):
        return data
    frame = data.copy()
    frame["grid_id"] = frame["grid_id"].astype(str)
    numeric_columns = frame.select_dtypes(include=[np.number]).columns.tolist()
    non_numeric_columns = [column for column in frame.columns if column not in numeric_columns and column not in {"grid_id", "date"}]
    aggregation = {column: "mean" for column in numeric_columns}
    aggregation.update({column: "first" for column in non_numeric_columns})
    collapsed = frame.groupby(["grid_id", "date"], as_index=False).agg(aggregation)
    return collapsed.sort_values(["grid_id", "date"]).reset_index(drop=True)


def add_vhi_targets(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.sort_values(["grid_id", "date"]).copy()
    if "vhi" not in frame.columns:
        ndvi_col = "modis_ndvi" if "modis_ndvi" in frame.columns and frame["modis_ndvi"].notna().sum() > frame["ndvi"].notna().sum() * 0.5 else "ndvi"
        lst_col = "modis_lst" if "modis_lst" in frame.columns and frame["modis_lst"].notna().sum() > frame["lst"].notna().sum() * 0.5 else "lst"
        vci = frame.groupby("grid_id")[ndvi_col].transform(minmax_vci)
        tci = frame.groupby("grid_id")[lst_col].transform(minmax_tci)
        frame["vci"] = vci
        frame["tci"] = tci
        frame["vhi"] = 0.5 * frame["vci"] + 0.5 * frame["tci"]
    frame["vhi_next_month"] = frame.groupby("grid_id")["vhi"].shift(-1)
    return frame


def validate_exports(base: pd.DataFrame, export_dir: Path, max_null_pct: float) -> dict:
    expected_months = [pd.Period(date, freq="M").strftime("%Y_%m") for date in sorted(base["date"].dropna().unique())]
    expected_set = set(expected_months)
    paths = sorted(export_dir.glob("agrishield_sindh_gee_*.csv"))
    by_month: dict[str, list[dict]] = {}
    file_reports = []
    for path in paths:
        month = parse_export_month(path.name)
        report = inspect_export_file(path, month, max_null_pct)
        file_reports.append(report)
        if month:
            by_month.setdefault(month, []).append(report)
    duplicate_months = {month: len(items) for month, items in sorted(by_month.items()) if len(items) > 1}
    missing_months = [month for month in expected_months if month not in by_month]
    invalid_files = [item for item in file_reports if not item["valid"]]
    too_null_months = []
    valid_months = []
    for month, items in sorted(by_month.items()):
        best = sorted(items, key=lambda item: (item["valid"], item["row_count"], item["file_size_bytes"]), reverse=True)[0]
        if best["valid"]:
            valid_months.append(month)
        if month in expected_set and best["null_pct"] is not None and best["null_pct"] > max_null_pct:
            too_null_months.append({"month": month, "null_pct": best["null_pct"], "best_file": best["file"]})
    return {
        "export_dir": str(export_dir),
        "expected_month_count": len(expected_months),
        "expected_first_month": expected_months[0] if expected_months else None,
        "expected_last_month": expected_months[-1] if expected_months else None,
        "file_count": len(paths),
        "unique_month_count": len(by_month),
        "valid_month_count": len(valid_months),
        "missing_months": missing_months,
        "duplicate_months": duplicate_months,
        "invalid_files": invalid_files,
        "too_null_months": too_null_months,
        "files": file_reports,
    }


def inspect_export_file(path: Path, month: str | None, max_null_pct: float) -> dict:
    base_report = {
        "file": path.name,
        "month": month,
        "file_size_bytes": path.stat().st_size,
        "row_count": 0,
        "column_count": 0,
        "missing_columns": EXPORT_COLUMNS,
        "null_pct": None,
        "valid": False,
        "status": "invalid",
    }
    try:
        frame = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        base_report["status"] = "empty"
        return base_report
    except Exception as exc:
        base_report["status"] = f"read_error: {exc}"
        return base_report
    missing_columns = [column for column in EXPORT_COLUMNS if column not in frame.columns]
    gee_columns = [column for column in EXPORT_COLUMNS if column in frame.columns and column not in {"grid_id", "longitude", "latitude", "date", "year", "month"}]
    if gee_columns:
        values = frame[gee_columns].replace(FILL_VALUE, np.nan).replace({-9999: np.nan, -9999.0: np.nan})
        null_pct = float(values.isna().mean().mean() * 100)
    else:
        null_pct = 100.0
    valid = len(frame) > 0 and {"grid_id", "date"}.issubset(frame.columns) and not missing_columns
    status = "valid" if valid and null_pct <= max_null_pct else "too_null" if valid else "invalid"
    return {
        "file": path.name,
        "month": month,
        "file_size_bytes": int(path.stat().st_size),
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "missing_columns": missing_columns,
        "null_pct": round(null_pct, 2),
        "valid": bool(valid and null_pct <= max_null_pct),
        "status": status,
    }


def parse_export_month(name: str) -> str | None:
    match = __import__("re").match(r"agrishield_sindh_gee_(\d{4})_(\d{2})(?:\(\d+\))?\.csv$", name)
    if not match:
        return None
    return f"{match.group(1)}_{match.group(2)}"


def build_broken_month_report(validation: dict) -> dict:
    broken = set(validation["missing_months"])
    broken.update(item["month"] for item in validation["invalid_files"] if item.get("month"))
    broken.update(item["month"] for item in validation["too_null_months"] if item.get("month"))
    return {
        "export_dir": validation["export_dir"],
        "broken_month_count": len(broken),
        "broken_months": sorted(broken),
        "empty_files": [item for item in validation["invalid_files"] if item["status"] == "empty"],
        "invalid_files": validation["invalid_files"],
        "missing_months": validation["missing_months"],
        "duplicate_months": validation["duplicate_months"],
        "too_null_months": validation["too_null_months"],
        "reexport_command_example": (
            "python scripts/expand_sindh_gee_dataset.py --mode gee-export --months "
            + ",".join(sorted(broken)[:24]).replace("_", "-")
            if broken
            else None
        ),
    }


def minmax_vci(values: pd.Series) -> pd.Series:
    low = values.quantile(0.05)
    high = values.quantile(0.95)
    denominator = max(high - low, 1e-6)
    return ((values - low) / denominator).clip(0, 1)


def minmax_tci(values: pd.Series) -> pd.Series:
    low = values.quantile(0.05)
    high = values.quantile(0.95)
    denominator = max(high - low, 1e-6)
    return (1 - ((values - low) / denominator)).clip(0, 1)


def add_climate_indices(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.copy()
    rainfall_col = "chirps_rainfall" if "chirps_rainfall" in frame.columns else "precipitation"
    if "rainfall_anomaly" not in frame.columns:
        climatology = frame.groupby(["grid_id", "month"])[rainfall_col].transform("mean")
        frame["rainfall_anomaly"] = frame[rainfall_col] - climatology
    for window in [1, 3, 6, 12]:
        rainfall_roll = frame.groupby("grid_id")[rainfall_col].transform(lambda item: item.rolling(window, min_periods=1).sum())
        frame[f"spi_{window}"] = zscore_by_grid_month(frame, rainfall_roll)
        water_balance = rainfall_roll - frame.groupby("grid_id")["evapotranspiration"].transform(lambda item: item.rolling(window, min_periods=1).sum()) if "evapotranspiration" in frame else rainfall_roll
        frame[f"spei_{window}"] = zscore_by_grid_month(frame, water_balance)
    return frame


def zscore_by_grid_month(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    temp = pd.DataFrame({"grid_id": frame["grid_id"], "month": frame["month"], "value": values})
    mean = temp.groupby(["grid_id", "month"])["value"].transform("mean")
    std = temp.groupby(["grid_id", "month"])["value"].transform("std").replace(0, np.nan)
    return ((temp["value"] - mean) / std).replace([np.inf, -np.inf], np.nan).fillna(0).clip(-3, 3)


def write_outputs(expanded: pd.DataFrame, output_path: Path, report_path: Path, status: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    expanded.to_csv(output_path, index=False)
    report = build_report(expanded, status=status)
    report_path.write_text(json.dumps(report, indent=2))
    print(json.dumps({"merged_dataset_path": str(output_path), "report_path": str(report_path), "status": status}, indent=2))


def build_report(data: pd.DataFrame, status: str, note: str | None = None) -> dict:
    missing = data.isna().sum().sort_values(ascending=False)
    new_present = [column for column in NEW_VARIABLES if column in data.columns]
    return {
        "status": status,
        "note": note,
        "gee_collections": GEE_COLLECTIONS,
        "rows": int(len(data)),
        "features": int(len(data.columns)),
        "grid_cells": int(data["grid_id"].nunique()),
        "date_min": str(data["date"].min().date()),
        "date_max": str(data["date"].max().date()),
        "new_variables_required": NEW_VARIABLES,
        "new_variables_present": new_present,
        "new_variables_missing": [column for column in NEW_VARIABLES if column not in data.columns],
        "missing_values_top": {column: int(value) for column, value in missing.head(30).items()},
        "feature_inventory": list(data.columns),
        "estimated_high_importance_variables": estimate_importance(data),
        "recommended_next_model": "Retrain the strict PSO Wavelet-Lag ExtraTrees + XGBoost ensemble first, then compare with a temporal attention LSTM/Transformer only after the enriched dataset is complete.",
    }


def estimate_importance(data: pd.DataFrame) -> list[dict]:
    candidate_columns = [column for column in NEW_VARIABLES if column in data.columns and pd.api.types.is_numeric_dtype(data[column])]
    if "ndvi" in data.columns and "lst" in data.columns and candidate_columns:
        proxy_vci = data.groupby("grid_id")["ndvi"].transform(lambda item: (item - item.quantile(0.05)) / max(item.quantile(0.95) - item.quantile(0.05), 1e-6)).clip(0, 1)
        proxy_tci = data.groupby("grid_id")["lst"].transform(lambda item: 1 - ((item - item.quantile(0.05)) / max(item.quantile(0.95) - item.quantile(0.05), 1e-6))).clip(0, 1)
        target = (0.5 * proxy_vci + 0.5 * proxy_tci).groupby(data["grid_id"]).shift(-1)
        scored = []
        for column in candidate_columns:
            valid = data[column].notna() & target.notna()
            if valid.sum() > 30:
                scored.append({"variable": column, "score": float(abs(data.loc[valid, column].corr(target.loc[valid]))), "method": "absolute_correlation_to_next_month_proxy_vhi"})
        if scored:
            return sorted(scored, key=lambda item: item["score"], reverse=True)
    return [
        {"variable": "soil_moisture", "score": None, "method": "domain_prior_until_gee_exports_are_merged"},
        {"variable": "rainfall_anomaly", "score": None, "method": "domain_prior_until_gee_exports_are_merged"},
        {"variable": "spi_3", "score": None, "method": "domain_prior_until_gee_exports_are_merged"},
        {"variable": "spei_3", "score": None, "method": "domain_prior_until_gee_exports_are_merged"},
        {"variable": "temperature", "score": None, "method": "domain_prior_until_gee_exports_are_merged"},
        {"variable": "evapotranspiration", "score": None, "method": "domain_prior_until_gee_exports_are_merged"},
        {"variable": "evi", "score": None, "method": "domain_prior_until_gee_exports_are_merged"},
        {"variable": "mndwi", "score": None, "method": "domain_prior_until_gee_exports_are_merged"},
        {"variable": "wind_speed", "score": None, "method": "domain_prior_until_gee_exports_are_merged"},
    ]


if __name__ == "__main__":
    main()
