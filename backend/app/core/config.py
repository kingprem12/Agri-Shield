from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AgriShield AI"
    environment: str = Field(default="local", alias="ENVIRONMENT")
    database_url: str = Field(default="sqlite:///./agrishield.sqlite3", alias="DATABASE_URL")
    jwt_secret_key: str = Field(default="change-me-in-production-use-env-secret-32-plus-bytes", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_minutes: int = Field(default=30, alias="ACCESS_TOKEN_MINUTES")
    refresh_token_days: int = Field(default=7, alias="REFRESH_TOKEN_DAYS")
    seed_admin_email: str = Field(default="", alias="SEED_ADMIN_EMAIL")
    seed_admin_password: str = Field(default="", alias="SEED_ADMIN_PASSWORD")
    seed_farmer_email: str = Field(default="", alias="SEED_FARMER_EMAIL")
    seed_farmer_password: str = Field(default="", alias="SEED_FARMER_PASSWORD")
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
