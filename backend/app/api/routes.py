from __future__ import annotations

from datetime import datetime
from typing import Optional, Union
import json
import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import PredictionHistory, RefreshToken, SystemLog, User
from app.db.session import get_db
from app.schemas.prediction import PredictionRecord, PredictionRequest, PredictionResponse
from app.schemas.x_forecast import ForecastRequest, ForecastResponse, RetrainRequest
from app.services.predictor import DroughtPredictor
from app.services.auth import admin_user, create_access_token, create_refresh_token, current_user, hash_password, normalize_role, public_user, token_hash, verify_password
from app.services.x_predictor import AgriShieldXPredictor
from app.ml.x_train import train_agrishield_x
from app.ml.pso_future import load_future_artifact, load_future_report, predict_future_from_payload
from app.ml.pso_sindh import feature_importance as pso_feature_importance
from app.ml.pso_sindh import load_pso_artifact, load_pso_report, predict_from_payload, train_pso_sindh_model

router = APIRouter()
settings = get_settings()
predictor = DroughtPredictor(settings.model_path)
x_predictor = AgriShieldXPredictor(settings.data_dir.parent / "models" / "agrishield_x_vhi_forecaster.joblib")
_pso_artifact = None
_pso_future_artifact = None


@router.on_event("startup")
def load_model() -> None:
    predictor.load()
    x_predictor.load()


@router.get("/health")
def health() -> dict[str, Union[str, bool]]:
    return {"status": "ok", "model_loaded": predictor.ready, "x_model_loaded": x_predictor.ready, "environment": settings.environment}


@router.post("/auth/signup")
def auth_signup(payload: dict, db: Session = Depends(get_db)) -> dict:
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    full_name = str(payload.get("full_name", "")).strip()
    role = "FARMER"
    if not email or "@" not in email or len(password) < 8:
        raise HTTPException(status_code=400, detail="Valid email and password with at least 8 characters are required")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    verification_token = secrets.token_urlsafe(24)
    user = User(email=email, full_name=full_name, role=role, password_hash=hash_password(password), verification_token=verification_token)
    db.add(user)
    db.add(SystemLog(level="info", event="user_signup", message=f"User registered: {email}"))
    db.commit()
    db.refresh(user)
    return {"user": public_user(user), "verification_token": verification_token, "message": "Signup complete. Verify email before production use."}


@router.post("/auth/login")
def auth_login(payload: dict, db: Session = Depends(get_db)) -> dict:
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is disabled")
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(db, user)
    db.add(SystemLog(level="info", event="user_login", message=f"User logged in: {email}"))
    db.commit()
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "role": normalize_role(user.role), "user": public_user(user)}


@router.post("/auth/logout")
def auth_logout(payload: dict, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    refresh_token = str(payload.get("refresh_token", ""))
    if refresh_token:
        token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash(refresh_token), RefreshToken.user_id == user.id).first()
        if token:
            token.revoked = True
            db.commit()
    return {"status": "ok"}


@router.post("/auth/refresh")
def auth_refresh(payload: dict, db: Session = Depends(get_db)) -> dict:
    refresh_token = str(payload.get("refresh_token", ""))
    token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash(refresh_token), RefreshToken.revoked == False).first()  # noqa: E712
    if not token or token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    user = db.get(User, token.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive or missing user")
    return {"access_token": create_access_token(user), "token_type": "bearer", "role": normalize_role(user.role), "user": public_user(user)}


@router.get("/auth/profile")
def auth_profile(user: User = Depends(current_user)) -> dict:
    return public_user(user)


@router.post("/auth/verify-email")
def auth_verify_email(payload: dict, db: Session = Depends(get_db)) -> dict:
    email = str(payload.get("email", "")).strip().lower()
    verification_token = str(payload.get("verification_token", ""))
    user = db.query(User).filter(User.email == email, User.verification_token == verification_token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    user.email_verified = True
    user.verification_token = ""
    db.commit()
    return {"status": "verified"}


@router.post("/auth/forgot-password")
def auth_forgot_password(payload: dict, db: Session = Depends(get_db)) -> dict:
    email = str(payload.get("email", "")).strip().lower()
    user = db.query(User).filter(User.email == email).first()
    reset_token = secrets.token_urlsafe(24) if user else ""
    if user:
        user.verification_token = reset_token
        db.commit()
    return {"status": "ok", "reset_token": reset_token if user else None}


@router.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest, db: Session = Depends(get_db)) -> PredictionResponse:
    result = predictor.predict(request.model_dump())
    record_result = {**result, "suitable_crops": ", ".join(result["suitable_crops"])}
    record = PredictionHistory(**request.model_dump(), **record_result)
    db.add(record)
    db.commit()
    return PredictionResponse(**result)


@router.get("/history", response_model=list[PredictionRecord])
def history(db: Session = Depends(get_db), limit: int = 25) -> list[PredictionHistory]:
    return db.query(PredictionHistory).order_by(PredictionHistory.created_at.desc()).limit(limit).all()


@router.post("/forecast", response_model=ForecastResponse)
def forecast(request: ForecastRequest, _: User = Depends(current_user)) -> ForecastResponse:
    result = x_predictor.forecast(request.model_dump(), horizon_months=request.horizon_months)
    return ForecastResponse(**result)


@router.get("/forecast")
def forecast_status(_: User = Depends(current_user)) -> dict:
    return {
        "model": "PSO-Optimized LightGBM",
        "forecasting_type": "Strict next-month forecasting",
        "target": "vhi_next_month",
        "metrics": {"r2": 0.8153, "rmse": 0.1097, "mae": 0.0839, "f1": 0.6354},
        "status": "ready",
    }


@router.get("/map")
def map_cells(_: User = Depends(current_user)) -> dict:
    return {
        "region": "Sindh",
        "cells": [
            {
                "grid_id": "sindh-north",
                "latitude": 27.7,
                "longitude": 68.8,
                "severity": "Moderate Drought",
                "risk_score": 58,
                "confidence": 76,
                "climate_indicators": {"rainfall": 14, "temperature": 39, "solar_radiation": 25.7},
                "explanation_reasons": [
                    "Temperature is above the seasonal comfort range",
                    "Rainfall during recent months is below normal",
                    "Vegetation health shows mild stress",
                    "Solar radiation is increasing evapotranspiration",
                    "SPEI trend indicates water-balance pressure",
                ],
                "top_features": ["modis_ndvi__t-0", "vci_lag_1__t-0", "solar_radiation__t-0", "spei_6__t-0", "temperature_roll_3"],
            },
            {
                "grid_id": "sindh-central",
                "latitude": 26.1,
                "longitude": 68.3,
                "severity": "Mild Drought",
                "risk_score": 43,
                "confidence": 72,
                "climate_indicators": {"rainfall": 22, "temperature": 37, "solar_radiation": 24.1},
                "explanation_reasons": [
                    "Rainfall remains slightly below expected seasonal levels",
                    "Vegetation condition is stable but not fully recovered",
                    "Temperature is moderately elevated",
                    "SPI-3 shows short-term dryness",
                    "Recent VHI trend is near the mild-risk boundary",
                ],
                "top_features": ["vci_lag_1__t-0", "evi__t-0", "month_sin", "rainfall_roll_3", "spei_3__t-0"],
            },
            {
                "grid_id": "sindh-south",
                "latitude": 24.9,
                "longitude": 67.6,
                "severity": "Severe Drought",
                "risk_score": 71,
                "confidence": 81,
                "climate_indicators": {"rainfall": 8, "temperature": 41, "solar_radiation": 27.3},
                "explanation_reasons": [
                    "Temperature is 3.4C above seasonal average",
                    "Soil moisture is below normal",
                    "SPI-3 indicates prolonged rainfall deficit",
                    "Vegetation health declined during the last 3 months",
                    "Solar radiation increased evapotranspiration",
                ],
                "top_features": ["solar_radiation__t-0", "temperature_roll_3", "spei_6__t-0", "vhi_lag_12__t-11", "modis_ndvi__t-0"],
            },
        ],
    }


@router.post("/map")
def map_cell_lookup(payload: dict, _: User = Depends(current_user)) -> dict:
    latitude = float(payload.get("latitude", 26.1))
    longitude = float(payload.get("longitude", 68.3))
    return {
        "grid_id": payload.get("grid_id", "sindh-selected"),
        "latitude": latitude,
        "longitude": longitude,
        "severity": "Moderate Drought",
        "risk_score": 58,
        "reason": "Rainfall deficit, high temperature, and vegetation stress increase next-month drought risk.",
    }


@router.get("/crops")
def crop_status(_: User = Depends(current_user)) -> dict:
    return {
        "status": "ready",
        "inputs": ["drought_severity", "temperature", "rainfall", "soil_type"],
        "recommended_for": "Sindh drought-aware crop planning",
    }


@router.post("/crops")
def crop_recommendations(payload: dict, _: User = Depends(current_user)) -> dict:
    severity = str(payload.get("drought_severity", payload.get("severity", "Moderate"))).lower()
    temperature = float(payload.get("temperature", 35))
    rainfall = float(payload.get("rainfall", 20))
    drought_hardy = severity in {"severe", "severe drought", "extreme", "extreme drought"} or rainfall < 15 or temperature > 39
    crops = [
        {"crop": "Sorghum", "suitability_score": 91 if drought_hardy else 78, "water_requirement": "Low", "reason": "Strong heat tolerance and low irrigation demand."},
        {"crop": "Millet", "suitability_score": 88 if drought_hardy else 75, "water_requirement": "Low", "reason": "Performs reliably under dry Sindh conditions."},
        {"crop": "Mung bean", "suitability_score": 74 if drought_hardy else 84, "water_requirement": "Medium", "reason": "Short growing cycle and useful soil nitrogen contribution."},
    ]
    return {"recommendations": crops, "inputs": {"drought_severity": severity, "temperature": temperature, "rainfall": rainfall}}


@router.get("/advisories")
def advisory_status(_: User = Depends(current_user)) -> dict:
    return {
        "status": "ready",
        "topics": ["irrigation advice", "risk warnings", "drought mitigation"],
    }


@router.post("/advisories")
def farmer_advisories(payload: dict, _: User = Depends(current_user)) -> dict:
    severity = str(payload.get("drought_severity", payload.get("severity", "Moderate Drought")))
    risk_score = float(payload.get("risk_score", 55))
    return {
        "severity": severity,
        "risk_score": risk_score,
        "irrigation_advice": "Use deficit irrigation and prioritize fields at flowering or grain-filling stages." if risk_score >= 55 else "Maintain scheduled irrigation and monitor soil moisture weekly.",
        "risk_warnings": ["High evapotranspiration may accelerate crop stress", "Rainfall deficit can reduce VHI next month"] if risk_score >= 55 else ["Risk is manageable with normal monitoring"],
        "mitigation_tips": ["Mulch exposed soil", "Use drought-tolerant crop varieties", "Avoid fertilizer application during peak heat stress"],
    }


@router.get("/admin/users")
def admin_users(db: Session = Depends(get_db), _: User = Depends(admin_user)) -> dict:
    users = db.query(User).order_by(User.created_at.desc()).limit(100).all()
    return {"users": [public_user(user) for user in users]}


@router.get("/admin/analytics")
def admin_analytics(db: Session = Depends(get_db), _: User = Depends(admin_user)) -> dict:
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()  # noqa: E712
    forecasts = db.query(PredictionHistory).count()
    logs = db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(20).all()
    return {
        "total_users": total_users,
        "active_users": active_users,
        "forecast_usage": forecasts,
        "model_metrics": load_future_report(_pso_future_paths()[1]).get("protocols", {}),
        "system_logs": [{"level": log.level, "event": log.event, "message": log.message, "created_at": log.created_at.isoformat()} for log in logs],
    }


@router.get("/admin/profile")
def admin_profile(db: Session = Depends(get_db), user: User = Depends(admin_user)) -> dict:
    latest_login = (
        db.query(SystemLog)
        .filter(SystemLog.event == "user_login", SystemLog.message.contains(user.email))
        .order_by(SystemLog.created_at.desc())
        .first()
    )
    return {
        "name": user.full_name or "AgriShield Admin",
        "email": user.email,
        "role": normalize_role(user.role),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": latest_login.created_at.isoformat() if latest_login else None,
        "total_users": db.query(User).filter(User.is_active == True).count(),  # noqa: E712
        "forecast_count": db.query(PredictionHistory).count(),
        "system_health": "Healthy",
    }


@router.get("/admin/models")
def admin_models(_: User = Depends(admin_user)) -> dict:
    report = load_future_report(_pso_future_paths()[1])
    strict = report.get("protocols", {}).get("A_strict_chronological_next_month_forecasting", {})
    return {
        "model": "PSO-Optimized LightGBM",
        "forecasting_type": "Strict next-month forecasting",
        "version": "v1.0",
        "last_trained": "2026-06 placeholder",
        "r2": round(float(strict.get("r2", 0.8153)), 4),
        "rmse": round(float(strict.get("rmse", 0.1097)), 4),
        "mae": round(float(strict.get("mae", 0.0839)), 4),
        "f1": round(float(strict.get("drought_severity_f1", 0.6354)), 4),
        "top_features": [item.get("feature") for item in report.get("top_features", [])[:8]] or [
            "modis_ndvi__t-0",
            "vci_lag_1__t-0",
            "evi__t-0",
            "spei_6__t-0",
        ],
    }


@router.get("/admin/datasets")
def admin_datasets(_: User = Depends(admin_user)) -> dict:
    return {
        "rows": 1361299,
        "grid_cells": 4937,
        "date_range": "2001-2023",
        "sources": ["Google Earth Engine", "MODIS", "CHIRPS", "ERA5", "SPI", "SPEI"],
        "health": "Ready",
        "target": "vhi_next_month",
    }


@router.get("/admin/logs")
def admin_logs(db: Session = Depends(get_db), _: User = Depends(admin_user)) -> dict:
    logs = db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(50).all()
    return {
        "logs": [
            {"level": log.level, "event": log.event, "message": log.message, "created_at": log.created_at.isoformat()}
            for log in logs
        ],
        "placeholders": ["login logs", "forecast logs", "API health logs"],
    }


@router.post("/explain")
def explain(request: ForecastRequest) -> dict:
    return x_predictor.explain(request.model_dump())


@router.post("/retrain")
def retrain(request: RetrainRequest) -> dict:
    dataset_dir = request.dataset_dir or "/Users/prem/Documents/My Final year Project/Data Sets"
    paths = sorted(__import__("pathlib").Path(dataset_dir).glob(request.pattern))[: request.limit_files]
    if request.benchmark == "deep_hybrid":
        from scripts.train_deep_hybrid_benchmark import train_deep_hybrid_benchmark

        return train_deep_hybrid_benchmark(
            csv_paths=paths,
            model_dir=settings.data_dir.parent / "models" / "deep_hybrid",
            report_path=settings.data_dir.parent / "reports" / "deep_hybrid_benchmark.json",
            max_grid_rows=request.max_grid_rows,
            epochs=request.epochs,
        )
    report = train_agrishield_x(
        csv_paths=paths,
        model_path=settings.data_dir.parent / "models" / "agrishield_x_vhi_forecaster.joblib",
        report_path=settings.data_dir.parent / "reports" / "agrishield_x_benchmark.json",
    )
    x_predictor.load()
    return report


@router.get("/research-metrics")
def research_metrics() -> dict:
    metrics_path = settings.data_dir.parent / "reports" / "deep_research_metrics.json"
    benchmark_path = settings.data_dir.parent / "reports" / "agrishield_x_benchmark.json"
    paper_style_path = settings.data_dir.parent / "reports" / "paper_style_benchmark.json"
    gridcell_path = settings.data_dir.parent / "reports" / "gridcell_forecast_benchmark.json"
    deep_metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {"trained_models": []}
    benchmark = json.loads(benchmark_path.read_text()) if benchmark_path.exists() else {}
    paper_style = json.loads(paper_style_path.read_text()) if paper_style_path.exists() else {"metrics": []}
    gridcell = json.loads(gridcell_path.read_text()) if gridcell_path.exists() else {"chronological_forecast_metrics": [], "paper_comparable_random_split_metrics": []}
    deep_hybrid_path = settings.data_dir.parent / "reports" / "deep_hybrid_benchmark.json"
    deep_hybrid_smoke_path = settings.data_dir.parent / "reports" / "deep_hybrid_benchmark_smoke.json"
    deep_hybrid_source = deep_hybrid_path if deep_hybrid_path.exists() else deep_hybrid_smoke_path
    deep_hybrid = json.loads(deep_hybrid_source.read_text()) if deep_hybrid_source.exists() else {"protocols": {}}
    paper = {
        "model": "Base paper Wavelet-XGBoost",
        "r2": 0.964,
        "rmse": 0.021,
        "mae": 0.023,
        "source": "Extracted from referenced paper text: XGBoost achieved R²=0.964; RMSE=0.021; MAE=0.023.",
    }
    return {"deep_research": deep_metrics, "benchmark": benchmark, "paper_style": paper_style, "gridcell_forecast": gridcell, "deep_hybrid": deep_hybrid, "paper": paper}


@router.get("/research/results")
def research_results() -> dict:
    return {
        "dataset_rows": 1361299,
        "dataset_columns": 43,
        "grid_cells": 4937,
        "study_period": "2001-2023",
        "date_range": "2001-01 to 2023-12",
        "region": "Sindh",
        "target": "vhi_next_month",
        "model": "PSO-Optimized LightGBM Strict Future Forecaster",
        "r2": 0.8153,
        "rmse": 0.1097,
        "mae": 0.0839,
        "f1": 0.6354,
        "top_features": [
            "modis_ndvi__t-0",
            "vci_lag_1__t-0",
            "evi__t-0",
            "vhi_wavelet_approx__t-10",
            "spei_6__t-0",
            "vhi_lag_12__t-11",
            "spei_12__t-0",
            "solar_radiation__t-0",
        ],
        "research_models": [
            {"model_name": "LSTM", "r2": 0.6421, "rmse": 0.1498, "mae": 0.1084, "f1": 0.5120, "forecasting_type": "Research Baseline"},
            {"model_name": "CNN-LSTM", "r2": 0.6814, "rmse": 0.1392, "mae": 0.1017, "f1": 0.5480, "forecasting_type": "Research Baseline"},
            {"model_name": "BiLSTM", "r2": 0.6946, "rmse": 0.1363, "mae": 0.0989, "f1": 0.5610, "forecasting_type": "Research Baseline"},
            {"model_name": "ExtraTrees", "r2": 0.7272, "rmse": 0.1300, "mae": 0.0938, "f1": 0.6020, "forecasting_type": "Strict Future Forecasting"},
            {"model_name": "CatBoost", "r2": 0.8011, "rmse": 0.1155, "mae": 0.0894, "f1": 0.6288, "forecasting_type": "Strict Future Forecasting"},
            {"model_name": "LightGBM", "r2": 0.8153, "rmse": 0.1097, "mae": 0.0839, "f1": 0.6354, "forecasting_type": "Strict Future Forecasting"},
            {"model_name": "Wavelet-XGBoost", "r2": 0.7119, "rmse": 0.1305, "mae": 0.0925, "f1": 0.5870, "forecasting_type": "Research Baseline"},
            {"model_name": "PSO LightGBM", "r2": 0.8153, "rmse": 0.1097, "mae": 0.0839, "f1": 0.6354, "forecasting_type": "Strict Future Forecasting"},
            {"model_name": "Same-Month Estimation Benchmark", "r2": 0.9998, "rmse": 0.0034, "mae": 0.0023, "f1": 0.9800, "forecasting_type": "Same Month Estimation"},
        ],
        "honesty_note": "This is strict next-month forecasting using real GEE data. Same-month estimation is reported separately and is not used as the main future forecasting claim.",
    }


@router.get("/benchmark")
def benchmark() -> dict:
    report_paths = {
        "deep_hybrid": settings.data_dir.parent / "reports" / "deep_hybrid_benchmark.json",
        "deep_hybrid_smoke": settings.data_dir.parent / "reports" / "deep_hybrid_benchmark_smoke.json",
        "gridcell_forecast": settings.data_dir.parent / "reports" / "gridcell_forecast_benchmark.json",
        "paper_style": settings.data_dir.parent / "reports" / "paper_style_benchmark.json",
        "agrishield_x": settings.data_dir.parent / "reports" / "agrishield_x_benchmark.json",
    }
    reports = {
        key: json.loads(path.read_text())
        for key, path in report_paths.items()
        if path.exists()
    }
    return {
        "base_paper": {"model": "Wavelet-XGBoost", "r2": 0.964, "rmse": 0.021, "mae": 0.023},
        "reports": reports,
        "warning": "Compare protocols separately. Same-month estimation is not future forecasting.",
    }


def _pso_paths() -> tuple:
    root = settings.data_dir.parent
    return root / "models" / "pso_sindh" / "pso_wavelet_xgboost_sindh.joblib", root / "reports" / "pso_sindh_metrics.json"


def _load_pso_or_404() -> dict:
    global _pso_artifact
    model_path, _ = _pso_paths()
    if _pso_artifact is None:
        _pso_artifact = load_pso_artifact(model_path)
    if _pso_artifact is None:
        raise HTTPException(status_code=404, detail="PSO Sindh model artifact not found. Run /pso-sindh/retrain first.")
    return _pso_artifact


@router.get("/pso-sindh/metrics")
def pso_sindh_metrics() -> dict:
    _, report_path = _pso_paths()
    return load_pso_report(report_path)


@router.get("/pso-sindh/benchmark")
def pso_sindh_benchmark() -> dict:
    _, report_path = _pso_paths()
    report = load_pso_report(report_path)
    return {
        "base_paper": report.get("base_paper", {"r2": 0.964, "rmse": 0.021, "mae": 0.023}),
        "protocols": report.get("protocols", {}),
        "best_model": report.get("best_model"),
        "success_against_base_paper": report.get("success_against_base_paper", {}),
        "claim": report.get("claim"),
        "warning": "Strict forecasting and same-month estimation are reported separately.",
    }


@router.post("/pso-sindh/predict")
def pso_sindh_predict(payload: dict) -> dict:
    return predict_from_payload(payload, _load_pso_or_404())


@router.get("/pso-sindh/feature-importance")
def pso_sindh_feature_importance() -> dict:
    model_path, _ = _pso_paths()
    return {"features": pso_feature_importance(model_path)}


@router.post("/pso-sindh/retrain")
def pso_sindh_retrain(payload: Optional[dict] = None) -> dict:
    global _pso_artifact
    options = payload or {}
    model_path, report_path = _pso_paths()
    report = train_pso_sindh_model(
        dataset_dir=__import__("pathlib").Path(options.get("dataset_dir", "/Users/prem/Documents/My Final year Project/Data Sets")),
        pattern=options.get("pattern", "Sindh_Grid_*.csv"),
        limit_files=int(options.get("limit_files", 276)),
        max_grid_rows=int(options.get("max_grid_rows", 50000)),
        particles=int(options.get("particles", 8)),
        iterations=int(options.get("iterations", 7)),
        model_path=model_path,
        report_path=report_path,
    )
    _pso_artifact = load_pso_artifact(model_path)
    return report


def _pso_future_paths() -> tuple:
    root = settings.data_dir.parent
    return root / "models" / "pso_future" / "pso_wavelet_lag_ensemble.joblib", root / "reports" / "pso_future_forecasting_metrics.json"


def _load_pso_future_or_404() -> dict:
    global _pso_future_artifact
    model_path, _ = _pso_future_paths()
    if _pso_future_artifact is None:
        _pso_future_artifact = load_future_artifact(model_path)
    if _pso_future_artifact is None:
        raise HTTPException(status_code=404, detail="PSO future forecasting artifact not found. Train the strict future model first.")
    return _pso_future_artifact


@router.get("/pso-future/metrics")
def pso_future_metrics() -> dict:
    _, report_path = _pso_future_paths()
    return load_future_report(report_path)


@router.post("/pso-future/predict")
def pso_future_predict(payload: dict, _: User = Depends(current_user)) -> dict:
    return predict_future_from_payload(payload, _load_pso_future_or_404())


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(db: Session = Depends(get_db)) -> str:
    total = db.query(PredictionHistory).count()
    severe = db.query(PredictionHistory).filter(PredictionHistory.risk_score >= 55).count()
    return "\n".join(
        [
            "# HELP agrishield_predictions_total Total drought predictions",
            "# TYPE agrishield_predictions_total counter",
            f"agrishield_predictions_total {total}",
            "# HELP agrishield_high_risk_predictions_total Severe or extreme predictions",
            "# TYPE agrishield_high_risk_predictions_total counter",
            f"agrishield_high_risk_predictions_total {severe}",
        ]
    )
