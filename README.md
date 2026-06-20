# AgriShield-X

AgriShield-X is a final-year major project for real-time agricultural drought forecasting over Sindh using Google Earth Engine satellite data, climate variables, heuristic optimization, machine learning, a secured FastAPI backend, and a React agriculture dashboard.

Repository: https://github.com/kingprem12/Agri-Shield

## Problem Statement

Agricultural drought develops when vegetation stress, rainfall shortage, heat, soil-water limitations, and seasonal climate pressure combine over time. Farmers need early warning before the next month begins, not only same-month reconstruction. AgriShield-X addresses this by predicting next-month Vegetation Health Index (`vhi_next_month`) from past and current satellite/climate indicators using a strict future-forecasting protocol.

## Dataset Summary

| Item | Value |
|---|---:|
| Region | Sindh |
| Study period | 2001-2023 |
| Rows | 1,361,299 |
| Grid cells | 4,937 |
| Target | `vhi_next_month` |
| Forecast type | Strict next-month forecasting |

Data sources and engineered variables include MODIS NDVI/LST, CHIRPS rainfall, ERA5 climate variables, EVI, SPI, SPEI, solar radiation, temperature, humidity, wind speed, lag features, rolling statistics, seasonal encoding, and wavelet-derived features. Soil moisture is used where available.

## Current Production Candidate

Model: **PSO-Optimized LightGBM** / **PSO LightGBM future-forecasting candidate**

Current strict future forecasting metrics:

| Metric | Value |
|---|---:|
| R2 | 0.8153 |
| RMSE | 0.1097 |
| MAE | 0.0839 |
| F1 | 0.6354 |

Research honesty note: the main result is strict next-month forecasting. Same-month estimation is reported separately and is not used as the future forecasting claim.

## Frontend Routes

Public routes:

- `/`
- `/auth`
- `/login`
- `/signup`

Authenticated FARMER routes:

- `/forecast-dashboard`
- `/interactive-map`
- `/historical-analysis`
- `/explainability`
- `/crop-recommendation`
- `/farmer-advisory`
- `/research-results`
- `/sindh-pso`
- `/classic-dashboard`
- `/analytics`
- `/benchmark`

ADMIN route:

- `/admin`

Unauthenticated users are redirected to `/auth` when opening protected pages. FARMER users cannot access `/admin`. ADMIN users can access all FARMER pages plus the admin console.

## Backend API Routes

Auth:

- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/logout`
- `POST /auth/refresh`
- `GET /auth/profile`
- `POST /auth/verify-email`
- `POST /auth/forgot-password`

Admin:

- `GET /admin/users`
- `GET /admin/analytics`

Forecasting and research:

- `GET /health`
- `POST /predict`
- `GET /history`
- `POST /forecast`
- `POST /explain`
- `GET /benchmark`
- `GET /research-metrics`
- `GET /research/results`
- `GET /pso-future/metrics`
- `POST /pso-future/predict`
- `GET /pso-sindh/metrics`
- `GET /pso-sindh/benchmark`
- `POST /pso-sindh/predict`
- `GET /pso-sindh/feature-importance`

Farmer support:

- `GET /map`
- `POST /crops`
- `POST /advisories`

Protected APIs require a JWT bearer token where appropriate.

## Authentication and Roles

Roles:

- `FARMER`
- `ADMIN`

Public signup creates FARMER accounts only. ADMIN accounts are seeded through backend environment variables:

```bash
SEED_ADMIN_EMAIL=admin@example.com
SEED_ADMIN_PASSWORD=replace-with-a-strong-password
```

Passwords are hashed in the backend. JWT access tokens and refresh tokens are used for session handling. Do not commit real secrets.

## Cloud Architecture

- Frontend: React + Vite static build hosted on AWS S3 static website hosting
- Backend: FastAPI service running in Docker on AWS EC2
- Database: PostgreSQL in Docker for deployment, SQLite for local development
- Infrastructure: Terraform definitions for EC2, S3, security group, IAM role, and SSM-capable instance profile
- Deployment helpers: shell scripts under `scripts/`

## Current Live URLs

Old live deployment:

- Frontend: http://agrishield-x-907739324681-ap-south-1.s3-website.ap-south-1.amazonaws.com
- Backend API: http://3.109.59.56:8000
- Health: http://3.109.59.56:8000/health
- Benchmark: http://3.109.59.56:8000/benchmark
- PSO future metrics: http://3.109.59.56:8000/pso-future/metrics
- EC2 public IP: `3.109.59.56`
- S3 bucket: `agrishield-x-907739324681-ap-south-1`

Newer S3 bucket observed:

- http://agrishield-x-parallel-20260621005550-frontend.s3-website.ap-south-1.amazonaws.com

Deployment status: PR #2 is merged into `main`, but the new claymorphism/auth UI and latest backend APIs are **not confirmed live** on the old EC2/S3 deployment. The old backend returns `404` for `/pso-future/metrics`, so redeployment is still pending.

## Local Run

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Tests

```bash
cd backend
PYTHONPATH=. python -m pytest tests

cd ../frontend
npm install
npm test -- --run
npm run build
```

## Terraform Usage

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# edit ssh_allowed_cidr and optional names
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
```

Destroy:

```bash
terraform destroy
```

Do not commit `terraform.tfvars`, `.terraform/`, Terraform state, `.env`, PEM files, datasets, or large model artifacts.

## Deployment Steps

1. Confirm the target EC2 and S3 bucket.
2. Confirm model artifacts exist on the EC2 host or copy them securely.
3. Configure production environment variables securely.
4. Pull latest `main` on the backend host.
5. Rebuild/restart backend Docker service.
6. Build frontend with the live API URL:

```bash
cd frontend
VITE_API_BASE_URL=http://3.109.59.56:8000 npm run build
aws s3 sync dist/ s3://agrishield-x-907739324681-ap-south-1 --delete
```

7. Verify auth, protected routes, `/health`, `/benchmark`, `/pso-future/metrics`, `/forecast`, `/map`, `/crops`, and `/advisories`.

## Pull Requests

- PR #1: https://github.com/kingprem12/Agri-Shield/pull/1
- PR #2: https://github.com/kingprem12/Agri-Shield/pull/2

## Project Structure

```text
backend/                 FastAPI API, auth, ML pipeline, scripts, tests
frontend/                React + Vite dashboard, auth context, pages, tests
infrastructure/terraform Terraform EC2/S3/IAM/security group definitions
scripts/                 Secret scan and deployment helpers
docs/                    Supporting architecture and report notes
monitoring/              Prometheus/Grafana assets when present
```
