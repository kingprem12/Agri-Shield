import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["MODEL_PATH"] = "models/does-not-exist.joblib"

from fastapi.testclient import TestClient

from app.db.models import User
from app.db.session import SessionLocal
from app.main import app
from app.services.auth import hash_password


def signup_and_login(client: TestClient, email: str = "farmer@test.local") -> str:
    client.post(
        "/auth/signup",
        json={"email": email, "password": "password123", "full_name": "Test Farmer", "role": "ADMIN"},
    )
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    assert response.json()["role"] == "FARMER"
    assert response.json()["user"]["role"] == "FARMER"
    return response.json()["access_token"]


def create_admin(email: str = "admin@test.local") -> str:
    with SessionLocal() as db:
        existing = db.query(User).filter(User.email == email).first()
        if not existing:
            db.add(
                User(
                    email=email,
                    full_name="Test Admin",
                    role="ADMIN",
                    password_hash=hash_password("password123"),
                    email_verified=True,
                )
            )
            db.commit()
    return email


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
    token = signup_and_login(client, "forecast@test.local")
    response = client.post(
        "/forecast",
        headers={"Authorization": f"Bearer {token}"},
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


def test_signup_is_farmer_only_and_farmer_cannot_access_admin():
    client = TestClient(app)
    token = signup_and_login(client, "farmer-rbac@test.local")
    profile = client.get("/auth/profile", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["role"] == "FARMER"

    admin_response = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert admin_response.status_code == 403


def test_admin_can_access_admin_analytics():
    client = TestClient(app)
    email = create_admin()
    login_response = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert login_response.status_code == 200
    assert login_response.json()["role"] == "ADMIN"
    assert login_response.json()["user"]["role"] == "ADMIN"
    token = login_response.json()["access_token"]
    response = client.get("/admin/analytics", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "total_users" in response.json()


def test_profile_normalizes_user_role_to_farmer():
    with SessionLocal() as db:
        email = "legacy-user@test.local"
        if not db.query(User).filter(User.email == email).first():
            db.add(
                User(
                    email=email,
                    full_name="Legacy User",
                    role="USER",
                    password_hash=hash_password("password123"),
                    email_verified=True,
                )
            )
            db.commit()
    client = TestClient(app)
    login_response = client.post("/auth/login", json={"email": "legacy-user@test.local", "password": "password123"})
    assert login_response.status_code == 200
    assert login_response.json()["role"] == "FARMER"
    profile = client.get("/auth/profile", headers={"Authorization": f"Bearer {login_response.json()['access_token']}"})
    assert profile.status_code == 200
    assert profile.json()["role"] == "FARMER"


def test_protected_forecast_requires_login():
    client = TestClient(app)
    response = client.post(
        "/forecast",
        json={
            "region": "Sindh",
            "horizon_months": 1,
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
    assert response.status_code == 401


def test_research_results_endpoint_returns_final_metrics():
    client = TestClient(app)
    response = client.get("/research/results")
    assert response.status_code == 200
    body = response.json()
    assert body["region"] == "Sindh"
    assert body["target"] == "vhi_next_month"
    assert body["dataset_rows"] == 1361299
    assert body["grid_cells"] == 4937
    assert body["r2"] == 0.8020
    assert body["rmse"] == 0.1151
    assert body["mae"] == 0.0890
    assert body["f1"] == 0.6306
