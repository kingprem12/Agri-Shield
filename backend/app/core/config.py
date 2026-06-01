from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AgriShield AI"
    environment: str = Field(default="local", alias="ENVIRONMENT")
    database_url: str = Field(default="sqlite:///./agrishield.sqlite3", alias="DATABASE_URL")
    model_path: Path = Field(default=Path("models/best_model.joblib"), alias="MODEL_PATH")
    data_dir: Path = Path("data")
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    class Config:
        env_file = ".env"
        populate_by_name = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
