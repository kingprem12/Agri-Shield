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


def seed_user(email: str, password: str, role: str, full_name: str) -> None:
    if not email or not password:
        return
    with SessionLocal() as db:
        existing = db.query(User).filter(User.email == email.lower()).first()
        if existing:
            return
        user = User(
            email=email.lower(),
            full_name=full_name,
            role=role,
            password_hash=hash_password(password),
            email_verified=True,
        )
        db.add(user)
        db.add(SystemLog(level="info", event="user_seeded", message=f"{role} account created from environment seed variables."))
        db.commit()


def seed_demo_users() -> None:
    seed_user(settings.seed_admin_email, settings.seed_admin_password, "ADMIN", "AgriShield Admin")
    seed_user(settings.seed_farmer_email, settings.seed_farmer_password, "FARMER", "AgriShield Farmer")


def create_app() -> FastAPI:
    Base.metadata.create_all(bind=engine)
    ensure_lightweight_schema_updates()
    seed_demo_users()
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
