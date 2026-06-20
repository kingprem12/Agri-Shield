# AgriShield-X Project Report

AgriShield-X is a final-year major project for strict next-month agricultural drought forecasting over Sindh using Google Earth Engine satellite data, climate variables, heuristic optimization, a secured backend, and a cloud-hosted frontend.

## Project Objective

The system predicts next-month agricultural drought severity so that farmers and administrators can make earlier irrigation, crop planning, and risk mitigation decisions. The main forecasting target is `vhi_next_month`.

## Dataset

| Item | Value |
|---|---:|
| Region | Sindh |
| Study period | 2001-2023 |
| Rows | 1,361,299 |
| Grid cells | 4,937 |
| Target | `vhi_next_month` |

Data sources include Google Earth Engine, MODIS NDVI, MODIS LST, CHIRPS rainfall, ERA5 climate variables, EVI, SPI, SPEI, solar radiation, temperature, humidity, wind speed, and soil moisture where available.

## Final Production Candidate

- Model: PSO-Optimized LightGBM / PSO LightGBM strict forecasting candidate
- Forecasting mode: strict next-month forecasting
- Target: `vhi_next_month`
- Leakage rule: target-month VHI/VCI/TCI are not used as next-month predictors

Current strict future forecasting metrics:

| Metric | Value |
|---|---:|
| R2 | 0.8153 |
| RMSE | 0.1097 |
| MAE | 0.0839 |
| F1 | 0.6354 |

Base paper metrics:

| Metric | Value |
|---|---:|
| R2 | 0.964 |
| RMSE | 0.021 |
| MAE | 0.023 |

The strict future forecasting model improves the project baseline but does not beat the base paper under strict next-month forecasting. Same-month estimation results are not used as the main future-forecasting claim.

## Application System

- Frontend: React + Vite agriculture dashboard
- UI: claymorphism green/earth visual system in merged source code
- Backend: FastAPI
- Auth: JWT access tokens, refresh tokens, FARMER and ADMIN roles
- Admin: users, analytics, system status, model metrics
- Farmer: forecasts, map, history, explainability, crops, advisories
- Cloud: AWS EC2 backend and AWS S3 frontend
- Infrastructure-as-code: Terraform for EC2, S3, IAM, security group, and outputs

## Current Live Deployment

Old deployment:

- Frontend: http://agrishield-x-907739324681-ap-south-1.s3-website.ap-south-1.amazonaws.com
- Backend API: http://3.109.59.56:8000
- Health: http://3.109.59.56:8000/health
- Benchmark: http://3.109.59.56:8000/benchmark
- PSO future metrics: http://3.109.59.56:8000/pso-future/metrics
- EC2 public IP: `3.109.59.56`

Observed newer frontend bucket:

- http://agrishield-x-parallel-20260621005550-frontend.s3-website.ap-south-1.amazonaws.com

Deployment status: PR #2 is merged, but the new claymorphism/auth UI and latest backend APIs are not confirmed live yet. The old backend currently returns `404` for `/pso-future/metrics`, so redeployment is pending.

## Research Honesty

The main result is strict next-month forecasting. Same-month estimation is useful for paper-style comparison and reconstruction, but it is not presented as future forecasting.

## Repository

- GitHub repository: https://github.com/kingprem12/Agri-Shield
- Main branch: https://github.com/kingprem12/Agri-Shield/tree/main
- PR #1: https://github.com/kingprem12/Agri-Shield/pull/1
- PR #2: https://github.com/kingprem12/Agri-Shield/pull/2
