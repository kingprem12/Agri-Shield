# AgriShield-X

Production-grade research prototype: Real-Time Agricultural Drought Forecasting using Multi-Source Remote Sensing, Deep Learning and Hybrid Ensemble Learning.

The repository also keeps the original AgriShield AI drought prediction flow, now extended with AgriShield-X VHI forecasting, Sindh CSV ingestion, wavelet features, baseline and hybrid ensembles, explainability endpoints, Prometheus/Grafana monitoring, and AWS deployment assets.

Cloud-based agricultural drought prediction and early warning system for a Final Year Engineering Major Project.

AgriShield AI predicts agricultural drought severity from satellite vegetation, land-surface temperature, rainfall, and weather features. The project includes automated ETL, wavelet feature engineering, model training, FastAPI inference, a React dashboard, PostgreSQL persistence, Docker, CI, and AWS deployment assets.

## Features

- MODIS NDVI, MODIS LST, CHIRPS rainfall, and NASA POWER weather ETL scripts
- Monthly aggregation, missing-value cleaning, wavelet transforms, lag features, and rolling averages
- XGBoost, Random Forest, and Linear Regression training with `TimeSeriesSplit`
- Best-model selection by RMSE and R², saved with Joblib
- FastAPI endpoints: `/health`, `/predict`, `/metrics`
- AgriShield-X endpoints: `/forecast`, `/explain`, `/benchmark`, `/retrain`
- PostgreSQL-backed prediction history
- React + Tailwind dashboard with Leaflet India map and Plotly charts
- Docker Compose for local full-stack execution
- GitHub Actions validation workflow
- AWS EC2/S3/Nginx/HTTPS deployment scripts and guide
- JWT authentication with FARMER and ADMIN roles
- Protected frontend routes for forecasting, maps, research results, advisories, crop recommendations, and admin analytics
- Terraform infrastructure for EC2, S3 static hosting, security groups, and SSM instance access

## Authentication and Roles

Unauthenticated users can access only the landing and auth pages. FARMER users can access forecasting, map, history, explainability, crop recommendation, advisory, research, and Sindh PSO pages. ADMIN users can access all FARMER pages plus the admin console.

Public signup always creates a FARMER account. ADMIN accounts are created safely from backend environment variables:

```bash
SEED_ADMIN_EMAIL=admin@example.com
SEED_ADMIN_PASSWORD=replace-with-a-strong-password
```

Never commit real secrets. Use `.env.example` as the placeholder reference.

## Quick Start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-research.txt
python scripts/run_etl.py --sample
python scripts/train_model.py
python scripts/train_agrishield_x.py --limit-files 36
python scripts/train_deep_hybrid_benchmark.py --dataset-dir "../Data Sets" --limit-files 276 --max-grid-rows 10000 --epochs 8
python scripts/generate_deep_hybrid_plots.py
uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Docker Local Run

```bash
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001` (`admin` / `agrishield`)

## Tests

```bash
cd backend
python -m pytest tests

cd ../frontend
npm test -- --run
npm run build
```

## Terraform

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
terraform destroy
```

Terraform state, local variables, PEM keys, datasets, model artifacts, and `.env` files are ignored and must not be committed.

## Current Research Result

The latest deep-hybrid benchmark is saved at `backend/reports/deep_hybrid_benchmark.json`.

Honest conclusion: the current best result beats the base paper metrics only under same-month VHI estimation, not strict future forecasting. Strict future forecasting, random split, same-month estimation, and spatial grid-cell holdout are reported separately.

## Project Structure

```text
backend/          FastAPI API, ETL, ML pipeline, tests
frontend/         React + Tailwind dashboard
infrastructure/  Nginx and AWS deployment assets
scripts/         Local and cloud deployment helpers
docs/            Architecture, ER, sequence, API, deployment, report
```

## Important Deployment Note

The AWS deployment scripts are production-oriented templates. They require your AWS account, IAM permissions, EC2 host, domain name, TLS email, and GitHub secrets before automatic deployment can run.
