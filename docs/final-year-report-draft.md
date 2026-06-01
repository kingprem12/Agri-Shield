# AgriShield AI: Cloud-Based Agricultural Drought Prediction and Early Warning System

## Abstract

AgriShield AI is a cloud-based agricultural drought prediction and early warning system that combines remote sensing, climate data, wavelet-based feature engineering, and machine learning. The system predicts drought severity from NDVI, land surface temperature, rainfall, and weather variables, then exposes predictions through a web dashboard and FastAPI service.

## Objectives

- Build an automated ETL pipeline for MODIS NDVI, MODIS LST, CHIRPS rainfall, and NASA POWER weather data.
- Engineer drought-relevant temporal features using monthly aggregation, lag variables, rolling averages, and wavelet transforms.
- Compare XGBoost, Random Forest, and Linear Regression using time-series validation.
- Deploy a cloud-ready backend, frontend, PostgreSQL database, and CI/CD workflow.

## Methodology

The methodology follows a hybrid modeling framework inspired by remote sensing drought forecasting research: vegetation, thermal, rainfall, and weather indicators are cleaned and aggregated monthly. Wavelet decomposition extracts low-frequency drought signals, while lag and rolling features represent delayed crop response. Models are evaluated with `TimeSeriesSplit` to avoid temporal leakage.

## System Modules

1. Data acquisition and ETL.
2. Feature engineering and model training.
3. FastAPI inference and metrics service.
4. React dashboard with map, form, and analytics.
5. PostgreSQL persistence.
6. Docker, CI/CD, and AWS deployment.

## Expected Outcome

The final system provides drought severity labels, probability/risk scores, recommendation text, map-based visualization, prediction history, and deployment assets suitable for demonstration and extension with live authenticated satellite data.

## Future Scope

- Integrate authenticated NASA AppEEARS production jobs.
- Add district boundary GeoJSON overlays.
- Train with historical drought labels from government datasets.
- Add SMS/WhatsApp farmer alert notifications.
- Integrate monitoring with Prometheus and Grafana.

