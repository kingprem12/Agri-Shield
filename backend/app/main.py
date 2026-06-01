from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import router
from app.core.config import get_settings
from app.db.models import PredictionHistory
from app.db.session import Base, engine

settings = get_settings()


def ensure_lightweight_schema_updates() -> None:
    if engine.url.get_backend_name() != "sqlite":
        return
    with engine.begin() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(prediction_history)"))}
        if "suitable_crops" not in columns:
            connection.execute(text("ALTER TABLE prediction_history ADD COLUMN suitable_crops VARCHAR(300) DEFAULT ''"))


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    ensure_lightweight_schema_updates()
    app = FastAPI(
        title=settings.app_name,
        description="Agricultural drought prediction and early warning API",
        version="1.0.0",
    )
    allow_credentials = "*" not in settings.cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
