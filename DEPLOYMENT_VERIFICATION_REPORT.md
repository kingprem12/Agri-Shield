# AgriShield-X Deployment Verification Report

Date: 2026-06-25  
Repository: `https://github.com/kingprem12/Agri-Shield`  
Branch audited: `main` after merging `production-role-ui-cleanup`

## Deployment Readiness

Status: **READY FOR AWS DEPLOYMENT**

Deployment readiness score: **95/100**

AgriShield-X is ready for backend/frontend redeployment after production environment variables are confirmed on the target server. No deployment was performed during this audit.

## Current Production Model

- Model: **PSO-Optimized LightGBM**
- Forecasting type: **Strict next-month forecasting**
- Target: `vhi_next_month`
- Region: Sindh
- Dataset: Google Earth Engine enriched climate and vegetation data

### Model Metrics

| Metric | Value |
|---|---:|
| R2 | 0.8153 |
| RMSE | 0.1097 |
| MAE | 0.0839 |
| F1 | 0.6354 |

### Model Artifact

GitHub does not store large model artifacts. The trained local artifact exists at:

`/Users/prem/Documents/My Final year Project/backend/models/pso_future/pso_wavelet_lag_ensemble.joblib`

Required deployment target path:

`/app/models/pso_future/pso_wavelet_lag_ensemble.joblib`

## Backend APIs

### Authentication

- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/logout`
- `POST /auth/refresh`
- `GET /auth/profile`

### Farmer APIs

- `GET /forecast`
- `POST /forecast`
- `GET /map`
- `POST /map`
- `GET /crops`
- `POST /crops`
- `GET /advisories`
- `POST /advisories`
- `POST /pso-future/predict`

### Admin APIs

- `GET /admin/users`
- `GET /admin/analytics`
- `GET /admin/profile`
- `GET /admin/models`
- `GET /admin/datasets`
- `GET /admin/logs`

Authorization expectations:

- Missing token returns `401`.
- FARMER token on admin APIs returns `403`.
- ADMIN token on admin APIs returns `200`.
- FARMER token on farmer APIs returns `200`.

## Frontend Routes

### Public

- `/`
- `/auth`
- `/auth/farmer`
- `/auth/admin`
- `/login`
- `/signup`
- `/help`

### Farmer

- `/dashboard`
- `/forecast`
- `/map`
- `/crops`
- `/advisories`
- `/history`
- `/profile`
- `/settings`
- `/research-results`
- `/sindh-pso`

### Admin

- `/admin`
- `/admin/users`
- `/admin/analytics`
- `/admin/models`
- `/admin/datasets`
- `/admin/logs`
- `/admin/profile`
- `/admin/settings`

## Terraform Resources

Terraform files are present under `infrastructure/terraform/`:

- AWS provider configuration
- EC2 backend instance
- S3 frontend static hosting bucket
- Security group
- IAM role and instance profile for SSM
- Outputs for backend URL, frontend URL, EC2 public IP, and bucket name
- `terraform.tfvars.example`

Terraform supports:

- `terraform init`
- `terraform plan`
- `terraform apply`
- `terraform destroy`

## AWS Checklist

Before deployment, verify:

- AWS CLI is authenticated.
- Region is `ap-south-1`.
- EC2 target is reachable through SSH or SSM.
- Security group allows backend port `8000`.
- S3 bucket exists or Terraform output provides a new bucket.
- Frontend build uses `VITE_API_BASE_URL=<backend_url>`.
- Production `.env` values are configured on backend host or container.
- No AWS keys are stored in code.

## Required Environment Variables

Backend:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `SEED_ADMIN_EMAIL`
- `SEED_ADMIN_PASSWORD`
- `SEED_FARMER_EMAIL`
- `SEED_FARMER_PASSWORD`
- `MODEL_PATH`

Frontend build:

- `VITE_API_BASE_URL`

## Verification Summary

- Backend tests: passed, `10 passed`
- Frontend tests: passed, `9 passed`
- Frontend build: passed
- Secret scan: passed
- Local HTTP/API smoke test: passed

Smoke-tested statuses:

- Admin login: `200`
- Farmer login: `200`
- Admin users as admin: `200`
- Admin analytics as admin: `200`
- Admin profile as admin: `200`
- Admin users as farmer: `403`
- Map without token: `401`
- Farmer forecast/map/crops/advisories APIs: `200`

## Remaining Deployment Blockers

No code blockers remain.

Operational reminders before deployment:

- Confirm the production backend has a strong `JWT_SECRET_KEY`.
- Copy or mount the trained model artifact to the backend container volume.
- Preserve the production database volume during redeployment.
- Configure S3 SPA fallback behavior or hash-routing fallback if direct route refresh is required on the static site.

