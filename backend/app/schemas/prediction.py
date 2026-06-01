from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PredictionRequest(BaseModel):
    state: str = Field(..., examples=["Maharashtra"])
    district: str = Field(..., examples=["Pune"])
    latitude: float = Field(..., ge=6.0, le=38.0)
    longitude: float = Field(..., ge=68.0, le=98.0)
    ndvi: float = Field(..., ge=-1.0, le=1.0)
    lst: float = Field(..., description="MODIS land surface temperature in Celsius")
    rainfall: float = Field(..., ge=0.0, description="Monthly CHIRPS rainfall in mm")
    temperature: float = Field(..., description="NASA POWER near-surface air temperature in Celsius")
    humidity: float = Field(..., ge=0.0, le=100.0)
    wind_speed: float = Field(..., ge=0.0)
    soil_moisture_proxy: float = Field(..., ge=0.0, le=1.0)


class PredictionResponse(BaseModel):
    severity: str
    probability: float
    risk_score: float
    recommendation: str
    suitable_crops: list[str]


class PredictionRecord(PredictionRequest, PredictionResponse):
    id: int
    created_at: datetime

    @field_validator("suitable_crops", mode="before")
    @classmethod
    def parse_crops(cls, value):
        if isinstance(value, str):
            return [crop.strip() for crop in value.split(",") if crop.strip()]
        return value

    class Config:
        from_attributes = True
