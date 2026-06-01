from typing import List, Optional

from pydantic import BaseModel, Field


class ForecastObservation(BaseModel):
    date: str
    NDVI: Optional[float] = None
    LST: Optional[float] = None
    Precipitation: Optional[float] = None
    ndvi: Optional[float] = None
    lst: Optional[float] = None
    rainfall: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    solar_radiation: Optional[float] = None
    wind_speed: Optional[float] = None
    soil_moisture: Optional[float] = None


class ForecastRequest(BaseModel):
    region: str = "Sindh"
    horizon_months: int = Field(default=3, ge=1, le=12)
    date: str = "2023-12"
    ndvi: float = 0.31
    lst: float = 41
    rainfall: float = 22
    temperature: float = 38
    humidity: float = 27
    solar_radiation: float = 26
    wind_speed: float = 4.8
    soil_moisture: float = 0.16
    observations: Optional[List[ForecastObservation]] = None


class ForecastPoint(BaseModel):
    date: str
    forecast_vhi: float
    severity: str
    confidence: float


class ForecastResponse(BaseModel):
    region: str
    horizon_months: int
    forecasts: List[ForecastPoint]


class RetrainRequest(BaseModel):
    dataset_dir: Optional[str] = None
    pattern: str = "Sindh_Grid_20*.csv"
    limit_files: int = Field(default=36, ge=6, le=276)
    benchmark: str = "agrishield_x"
    max_grid_rows: int = Field(default=50000, ge=1000, le=250000)
    epochs: int = Field(default=20, ge=1, le=120)
