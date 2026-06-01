from __future__ import annotations

from typing import Union
import json

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import PredictionHistory
from app.db.session import get_db
from app.schemas.prediction import PredictionRecord, PredictionRequest, PredictionResponse
from app.schemas.x_forecast import ForecastRequest, ForecastResponse, RetrainRequest
from app.services.predictor import DroughtPredictor
from app.services.x_predictor import AgriShieldXPredictor
from app.ml.x_train import train_agrishield_x

router = APIRouter()
settings = get_settings()
predictor = DroughtPredictor(settings.model_path)
x_predictor = AgriShieldXPredictor(settings.data_dir.parent / "models" / "agrishield_x_vhi_forecaster.joblib")


@router.on_event("startup")
def load_model() -> None:
    predictor.load()
    x_predictor.load()


@router.get("/health")
def health() -> dict[str, Union[str, bool]]:
    return {"status": "ok", "model_loaded": predictor.ready, "x_model_loaded": x_predictor.ready, "environment": settings.environment}


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
def forecast(request: ForecastRequest) -> ForecastResponse:
    result = x_predictor.forecast(request.model_dump(), horizon_months=request.horizon_months)
    return ForecastResponse(**result)


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
