from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
import requests


@dataclass
class RegionBounds:
    name: str
    west: float
    south: float
    east: float
    north: float


SINDH_BOUNDS = RegionBounds("Sindh", 66.6, 23.3, 71.1, 28.6)


class GoogleEarthEngineAdapter:
    def fetch_monthly(self, bounds: RegionBounds, start: str, end: str) -> pd.DataFrame:
        try:
            import ee
        except ImportError as exc:
            raise RuntimeError("earthengine-api is not installed. Install it and run `earthengine authenticate`.") from exc
        ee.Initialize()
        geometry = ee.Geometry.Rectangle([bounds.west, bounds.south, bounds.east, bounds.north])
        start_date = ee.Date(start)
        end_date = ee.Date(end)
        months = end_date.difference(start_date, "month").round()
        indices = ee.List.sequence(0, months.subtract(1))

        def monthly(index):
            current = start_date.advance(index, "month")
            next_month = current.advance(1, "month")
            ndvi = ee.ImageCollection("MODIS/061/MOD13Q1").filterDate(current, next_month).select("NDVI").mean().multiply(0.0001)
            lst = ee.ImageCollection("MODIS/061/MOD11A2").filterDate(current, next_month).select("LST_Day_1km").mean().multiply(0.02).subtract(273.15)
            chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate(current, next_month).select("precipitation").sum()
            image = ndvi.rename("NDVI").addBands(lst.rename("LST")).addBands(chirps.rename("Precipitation"))
            stats = image.reduceRegion(ee.Reducer.mean(), geometry, 5000, maxPixels=1e13)
            return ee.Feature(None, stats).set({"date": current.format("YYYY-MM"), "region": bounds.name})

        features = ee.FeatureCollection(indices.map(monthly)).getInfo()["features"]
        return pd.DataFrame([feature["properties"] for feature in features])


class NasaPowerAdapter:
    def fetch_monthly(self, latitude: float, longitude: float, start_year: int, end_year: int) -> pd.DataFrame:
        response = requests.get(
            "https://power.larc.nasa.gov/api/temporal/monthly/point",
            params={
                "parameters": "T2M,RH2M,ALLSKY_SFC_SW_DWN,WS2M",
                "community": "AG",
                "longitude": longitude,
                "latitude": latitude,
                "start": start_year,
                "end": end_year,
                "format": "JSON",
            },
            timeout=45,
        )
        response.raise_for_status()
        params = response.json()["properties"]["parameter"]
        rows = []
        for key in params["T2M"]:
            if key.endswith("13"):
                continue
            rows.append(
                {
                    "date": pd.to_datetime(key, format="%Y%m").strftime("%Y-%m"),
                    "temperature": params["T2M"][key],
                    "humidity": params["RH2M"][key],
                    "solar_radiation": params["ALLSKY_SFC_SW_DWN"][key],
                    "wind_speed": params["WS2M"][key],
                }
            )
        return pd.DataFrame(rows)


class SoilGridsAdapter:
    def fetch_point(self, latitude: float, longitude: float) -> dict[str, float]:
        response = requests.get(
            "https://rest.isric.org/soilgrids/v2.0/properties/query",
            params={
                "lat": latitude,
                "lon": longitude,
                "property": ["sand", "clay", "soc"],
                "depth": "0-5cm",
                "value": "mean",
            },
            timeout=45,
        )
        response.raise_for_status()
        layers = response.json().get("properties", {}).get("layers", [])
        values = {}
        for layer in layers:
            name = layer["name"]
            mean = layer["depths"][0]["values"]["mean"]
            values[name] = mean
        sand = values.get("sand", 350)
        clay = values.get("clay", 220)
        soil_moisture = max(0.05, min(0.9, (clay / (sand + clay + 1)) * 0.8))
        return {"sand": sand, "clay": clay, "soil_organic_carbon": values.get("soc", 80), "soil_moisture": soil_moisture}

