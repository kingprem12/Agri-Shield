# AgriShield-X Research Report

## Title

AgriShield-X: Real-Time Agricultural Drought Forecasting using Multi-Source Remote Sensing, Deep Learning and Hybrid Ensemble Learning.

## Research Aim

Forecast future Vegetation Health Index (VHI) and drought severity using multi-source satellite, weather, soil, and custom CSV datasets. The local prototype is trained on Sindh Google Earth Engine CSV exports and can be extended to live Google Earth Engine, NASA POWER, CHIRPS, MODIS, and SoilGrids ingestion.

## Data Sources

| Source | Variables | Implementation |
|---|---:|---|
| Google Earth Engine | MODIS NDVI, MODIS LST, CHIRPS rainfall | `backend/app/services/data_sources.py` |
| NASA POWER | Temperature, humidity, solar radiation, wind speed | `NasaPowerAdapter` |
| SoilGrids | Sand, clay, SOC, soil moisture proxy | `SoilGridsAdapter` |
| Custom CSV | Sindh grid and monthly drought CSVs | `read_custom_csvs` |

## Feature Engineering

The AgriShield-X pipeline generates NDVI, LST, rainfall, temperature, humidity, evapotranspiration, soil moisture, VCI, TCI, VHI, SPI, SPEI, month/season encodings, 1/2/3/6 month lags, 3/6/12 month rolling means, and causal wavelet approximation/detail coefficients. Strict next-month forecasting uses shifted historical rolling and wavelet features to avoid target-month leakage.

## Models

| Family | Model |
|---|---|
| Baselines | Random Forest, AdaBoost, XGBoost |
| Deep Learning | PyTorch LSTM, CNN-LSTM, BiLSTM, GRU |
| Heuristic Hybrids | Optuna-optimized Wavelet-XGBoost, PSO-optimized Wavelet-XGBoost |
| Proposed Hybrid | Wavelet + CNN/BiLSTM/GRU embeddings + XGBoost/ExtraTrees stacking ensemble |

Installing `backend/requirements-research.txt` enables Earth Engine, SHAP, Optuna, PyTorch, TensorFlow expansion, and plotting utilities.

## Evaluation Metrics

Models are evaluated using R², RMSE, MAE, MAPE, and Explained Variance under four separate protocols: strict chronological next-month forecasting, paper-comparable random split, same-month VHI estimation, and spatial grid-cell holdout.

## Current Local Benchmark

See `backend/reports/deep_hybrid_benchmark.json` for the current deep-hybrid comparison and `backend/reports/agrishield_x_benchmark.json` for the earlier AgriShield-X benchmark.

## Limitations

- Current deep-hybrid run uses all available months but a bounded real-grid sample for local runtime.
- Same-month estimation can beat the base paper metrics, but this is not a future forecasting result.
- Live GEE requires `earthengine-api` installation and authentication.

## Future Work

- Replace fallback deep-learning adapters with TensorFlow LSTM, BiLSTM, CNN-LSTM, and TFT training.
- Add district boundary GeoJSON layers for Sindh and Pakistan.
- Integrate SHAP TreeExplainer once `shap` is installed.
- Add Optuna study persistence in PostgreSQL.
