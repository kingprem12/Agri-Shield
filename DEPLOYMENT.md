# AgriShield-X Deployment Guide

This guide describes the current deployment state and the safe steps for redeploying the merged `main` branch. Do not commit secrets, PEM files, Terraform state, raw datasets, or large model artifacts.

## Current Deployment State

Repository: https://github.com/kingprem12/Agri-Shield

Current old live deployment:

- Frontend: http://agrishield-x-907739324681-ap-south-1.s3-website.ap-south-1.amazonaws.com
- Backend API: http://3.109.59.56:8000
- Health: http://3.109.59.56:8000/health
- Benchmark: http://3.109.59.56:8000/benchmark
- PSO future metrics: http://3.109.59.56:8000/pso-future/metrics
- EC2 public IP: `3.109.59.56`
- EC2 instance: `i-037cdb7d5abbf5781`
- S3 bucket: `agrishield-x-907739324681-ap-south-1`

Observed newer frontend bucket:

- http://agrishield-x-parallel-20260621005550-frontend.s3-website.ap-south-1.amazonaws.com

Status: the old backend is reachable and `/health` returns OK, but `/pso-future/metrics` currently returns `404`. This means the merged claymorphism/auth UI and latest backend APIs are not confirmed live on the old deployment. Redeployment is pending.

## Required Environment Variables

Backend:

```bash
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DB_NAME
JWT_SECRET_KEY=replace-with-a-strong-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=30
REFRESH_TOKEN_DAYS=7
SEED_ADMIN_EMAIL=admin@example.com
SEED_ADMIN_PASSWORD=replace-with-a-strong-admin-password
MODEL_PATH=/app/models/best_model.joblib
```

Frontend build:

```bash
VITE_API_BASE_URL=http://3.109.59.56:8000
```

AWS:

```bash
AWS_REGION=ap-south-1
```

Use the AWS CLI profile or environment variables already configured on the deployment machine. Never paste or commit AWS secrets.

## Local Verification Before Deployment

Backend:

```bash
cd backend
PYTHONPATH=. python -m pytest tests
```

Frontend:

```bash
cd frontend
npm install
npm test -- --run
npm run build
```

Secret scan:

```bash
scripts/check_secrets.sh
```

## Backend Deployment to Existing EC2

Use the existing EC2 only if SSH access with the correct key is confirmed and model/database volumes must be preserved.

```bash
ssh ec2-user@3.109.59.56
cd /opt/agrishield-ai
git pull origin main
docker compose up -d --build postgres backend
```

Preserve:

- production `.env` or container environment variables
- database volume
- model artifact volume

Required model artifacts on the server:

- `/app/models/best_model.joblib`
- `/app/models/agrishield_x_vhi_forecaster.joblib`
- `/app/models/pso_future/pso_wavelet_lag_ensemble.joblib`

Verify backend:

```bash
curl http://3.109.59.56:8000/health
curl http://3.109.59.56:8000/benchmark
curl http://3.109.59.56:8000/pso-future/metrics
```

Auth verification:

- `POST /auth/signup`
- `POST /auth/login`
- `GET /auth/profile`
- `GET /admin/analytics` with ADMIN token

## Frontend Deployment to S3

```bash
cd frontend
VITE_API_BASE_URL=http://3.109.59.56:8000 npm run build
aws s3 sync dist/ s3://agrishield-x-907739324681-ap-south-1 --delete
```

Verify routes:

- `/`
- `/auth`
- `/login`
- `/signup`
- `/forecast-dashboard`
- `/interactive-map`
- `/historical-analysis`
- `/explainability`
- `/crop-recommendation`
- `/farmer-advisory`
- `/research-results`
- `/sindh-pso`
- `/admin`

## Terraform Deployment Option

Terraform creates a cleaner AWS setup with EC2, S3, security group, IAM role, and SSM-capable instance profile.

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
```

Destroy support:

```bash
terraform destroy
```

Do not commit `terraform.tfvars`, `.terraform/`, or state files.

## Old EC2 vs New EC2

Reuse old EC2 if:

- SSH access with `agrishield-x-key` works.
- Existing model artifacts must be preserved.
- Existing database state must be preserved.

Create or migrate to Terraform EC2 if:

- SSH/PEM access is unreliable.
- SSM Session Manager is preferred.
- A cleaner reproducible deployment is required.

Current old EC2 has no IAM instance profile, so SSM is not available there unless the instance is modified later.

## Troubleshooting

- `401`: login required or expired/invalid JWT.
- `403`: authenticated user lacks ADMIN role.
- `/pso-future/metrics` returns `404`: latest backend/model report is not deployed or artifact/report path is missing.
- Frontend shows old pages: S3 bucket was not synced or browser cache is stale.
- Admin login missing: set `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` on backend before first startup.
