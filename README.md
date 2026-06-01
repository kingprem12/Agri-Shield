# AgriShield-X

AgriShield-X is a final-year major project for real-time agricultural drought forecasting using remote sensing, deep learning, heuristic optimization, hybrid ensemble learning, and cloud deployment.

The system predicts Vegetation Health Index (VHI) and drought severity from real satellite and climate features including NDVI, LST, rainfall, temperature, humidity, evapotranspiration, soil moisture, VCI, TCI, SPI, SPEI, lags, rolling windows, and wavelet features.

## Architecture

```text
frontend/                 React + Vite dashboard
backend/                  FastAPI API, ML pipelines, tests, reports
backend/app/ml/           Feature engineering, deep learning, hybrid models
backend/scripts/          Training and benchmark scripts
infrastructure/terraform/ AWS EC2 + S3 infrastructure as code
scripts/                  Safe deployment and secret-scan helpers
docs/                     Supporting architecture and research notes
monitoring/               Prometheus and Grafana configuration
```

## Implemented Models

- LSTM, CNN-LSTM, BiLSTM, and GRU sequence regressors in PyTorch
- CNN grid-image model for NDVI/LST/rainfall image-like patches
- Wavelet + XGBoost
- ExtraTrees and XGBoost baselines
- PSO-optimized Wavelet XGBoost
- Optuna path with random-search fallback
- Proposed Wavelet + CNN/BiLSTM/GRU embeddings + XGBoost stacking ensemble

Large trained model artifacts are intentionally ignored by Git. Store production model files on the deployment host, an attached volume, or an object store.

## Local Run

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm test -- --run
npm run dev
```

Open `http://localhost:5173`.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

Services:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001`

## API Endpoints

- `GET /health`
- `POST /predict`
- `POST /forecast`
- `POST /explain`
- `GET /research-metrics`
- `GET /benchmark`
- `POST /retrain`
- `GET /metrics`

## Benchmark Summary

Base paper metrics:

| Metric | Base paper |
|---|---:|
| R2 | 0.964 |
| RMSE | 0.021 |
| MAE | 0.023 |

Current best reported results:

| Protocol | Best model | R2 | RMSE | MAE | MAPE |
|---|---|---:|---:|---:|---:|
| Strict future forecasting | Proposed Wavelet + CNN/BiLSTM/GRU + XGBoost stacking | 0.8897 | 0.0581 | 0.0473 | 0.1092 |
| Paper-comparable random split | ExtraTrees random split | 0.6795 | 0.1367 | 0.0957 | 0.7114 |
| Same-month VHI estimation | Wavelet-XGBoost VHI estimator | 0.9996 | 0.0050 | 0.0038 | 0.0137 |
| Spatial grid-cell holdout | ExtraTrees unseen-grid holdout | 0.6634 | 0.1434 | 0.1063 | 0.6674 |

Honest conclusion: the project beats the base paper only under same-month VHI estimation/reconstruction. It does not yet beat the base paper under strict future forecasting.

## Terraform Deployment

Terraform lives in `infrastructure/terraform`.

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

Required values include:

- `ssh_allowed_cidr`
- `key_name`
- optional unique `bucket_name`

Destroy:

```bash
terraform destroy
```

## Safe Deployment Scripts

Backend:

```bash
export EC2_HOST="<ec2-public-ip>"
export EC2_USER="ec2-user"
export SSH_KEY_PATH="/path/to/key.pem"
export REPO_URL="https://github.com/kingprem12/Agri-Shield.git"
export BRANCH="safe-terraform-deployment"
export POSTGRES_PASSWORD="<local-secret-value>"
./scripts/deploy_backend_ec2.sh
```

Frontend:

```bash
export S3_BUCKET="<terraform-output-bucket>"
export VITE_API_BASE_URL="http://<ec2-public-ip>:8000"
./scripts/deploy_frontend_s3.sh
```

Secret scan:

```bash
./scripts/check_secrets.sh
```

## Secret Handling

Never commit:

- `.env` or `.env.*`
- AWS keys
- PEM/private keys
- Terraform state or `terraform.tfvars`
- credentials files
- `node_modules`, virtual environments, caches, or generated build folders
- large datasets and large model artifacts

Use `.env.example` and `terraform.tfvars.example` only for safe placeholders.
