# AgriShield-X Project Report

AgriShield-X is a final-year major project for strict next-month agricultural drought forecasting over Sindh using Google Earth Engine satellite and climate data.

## Final Production Candidate

- Model: PSO-Optimized LightGBM / enriched future forecasting ensemble candidate
- Target: `vhi_next_month`
- Forecasting mode: strict chronological next-month forecasting
- Dataset: 1,361,299 rows, 4,937 grid cells, 2001-2023
- Current strict metrics: R2 0.8153, RMSE 0.1097, MAE 0.0839, F1 0.6354

## System

- Frontend: React + Vite agriculture dashboard
- Backend: FastAPI
- Auth: JWT access tokens, refresh tokens, FARMER and ADMIN roles
- Cloud: AWS EC2 backend, S3 frontend, Terraform infrastructure
- ML assets: preserved locally and excluded from Git when too large

## Research Honesty

The main claim is strict next-month forecasting. Same-month estimation is reported separately and is not used as the future-forecasting result.
