import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["MODEL_PATH"] = "models/does-not-exist.joblib"

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predict_endpoint_returns_severity():
    client = TestClient(app)
    payload = {
        "state": "Maharashtra",
        "district": "Pune",
        "latitude": 18.52,
        "longitude": 73.85,
        "ndvi": 0.32,
        "lst": 39.0,
        "rainfall": 28.0,
        "temperature": 36.0,
        "humidity": 31.0,
        "wind_speed": 4.2,
        "soil_moisture_proxy": 0.18,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["severity"] in {"No Drought", "Mild Drought", "Moderate Drought", "Severe Drought", "Extreme Drought"}
    assert 0 <= body["probability"] <= 1
    assert body["suitable_crops"]


def test_forecast_endpoint_returns_future_vhi():
    client = TestClient(app)
    response = client.post(
        "/forecast",
        json={
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
            "soil_moisture": 0.14,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["forecasts"]) == 3
    assert "forecast_vhi" in body["forecasts"][0]
