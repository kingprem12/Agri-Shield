from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.api.routes import router
from app.core.config import get_settings
from app.db.models import PredictionHistory, SystemLog, User
from app.db.session import Base, SessionLocal, engine
from app.services.auth import hash_password

settings = get_settings()


def ensure_lightweight_schema_updates() -> None:
    if engine.url.get_backend_name() != "sqlite":
        return
    with engine.begin() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(prediction_history)"))}
        if "suitable_crops" not in columns:
            connection.execute(text("ALTER TABLE prediction_history ADD COLUMN suitable_crops VARCHAR(300) DEFAULT ''"))


def seed_admin_user() -> None:
    if not settings.seed_admin_email or not settings.seed_admin_password:
        return
    with SessionLocal() as db:
        existing = db.query(User).filter(User.email == settings.seed_admin_email.lower()).first()
        if existing:
            return
        admin = User(
            email=settings.seed_admin_email.lower(),
            full_name="AgriShield Admin",
            role="ADMIN",
            password_hash=hash_password(settings.seed_admin_password),
            email_verified=True,
        )
        db.add(admin)
        db.add(SystemLog(level="info", event="admin_seeded", message="Admin account created from environment seed variables."))
        db.commit()


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    ensure_lightweight_schema_updates()
    seed_admin_user()
    app = FastAPI(
        title=settings.app_name,
        description="Agricultural drought prediction and early warning API",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
