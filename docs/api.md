# API Documentation

Base URL: `http://localhost:8000`

## `GET /health`

Returns service status and model readiness.

```json
{
  "status": "ok",
  "model_loaded": true,
  "environment": "local"
}
```

## `POST /predict`

Request:

```json
{
  "state": "Maharashtra",
  "district": "Pune",
  "latitude": 18.52,
  "longitude": 73.85,
  "ndvi": 0.42,
  "lst": 36,
  "rainfall": 45,
  "temperature": 34,
  "humidity": 38,
  "wind_speed": 3.8,
  "soil_moisture_proxy": 0.25
}
```

Response:

```json
{
  "severity": "Moderate Drought",
  "probability": 0.49,
  "risk_score": 49.0,
  "recommendation": "Increase field monitoring and recommend supplemental irrigation where available."
}
```

## `GET /history`

Returns recent prediction records. Optional query parameter: `limit`.

## `GET /metrics`

Returns Prometheus-style plaintext metrics for prediction totals and high-risk alerts.

## `POST /forecast`

Forecasts future VHI and drought severity with the AgriShield-X model.

Request:

```json
{
  "region": "Sindh",
  "horizon_months": 3,
  "date": "2023-12",
  "ndvi": 0.28,
  "lst": 42,
  "rainfall": 18,
  "temperature": 39,
  "humidity": 24,
  "solar_radiation": 27,
  "wind_speed": 5.4,
  "soil_moisture": 0.14
}
```

Response:

```json
{
  "region": "Sindh",
  "horizon_months": 3,
  "forecasts": [
    {
      "date": "2024-01",
      "forecast_vhi": 68.95,
      "severity": "No Drought",
      "confidence": 0.85
    }
  ]
}
```

## `POST /explain`

Returns SHAP-compatible fallback feature importance for the forecast request. Install `backend/requirements-research.txt` to extend this with real SHAP explainers.

## `POST /retrain`

Retrains AgriShield-X using custom CSV datasets.

```json
{
  "dataset_dir": "/Users/prem/Documents/My Final year Project/Data Sets",
  "pattern": "Sindh_Grid_20*.csv",
  "limit_files": 36
}
```
