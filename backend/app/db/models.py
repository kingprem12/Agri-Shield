from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PredictionHistory(Base):
    __tablename__ = "prediction_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    state: Mapped[str] = mapped_column(String(80), index=True)
    district: Mapped[str] = mapped_column(String(120), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    ndvi: Mapped[float] = mapped_column(Float)
    lst: Mapped[float] = mapped_column(Float)
    rainfall: Mapped[float] = mapped_column(Float)
    temperature: Mapped[float] = mapped_column(Float)
    humidity: Mapped[float] = mapped_column(Float)
    wind_speed: Mapped[float] = mapped_column(Float)
    soil_moisture_proxy: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(40), index=True)
    probability: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float)
    recommendation: Mapped[str] = mapped_column(String(300))
    suitable_crops: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
