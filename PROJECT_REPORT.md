# AgriShield-X Project Report

## Title

AgriShield-X: Real-Time Agricultural Drought Forecasting using Deep Learning, Heuristic Optimization, Remote Sensing and Cloud Deployment.

## Objective

Build a deployable drought forecasting system that predicts VHI and drought severity using real remote-sensing and climate datasets, with honest evaluation across forecasting, estimation, random split, and spatial holdout protocols.

## Data and Features

The project uses local real monthly grid-cell drought data derived from remote sensing and climate variables. Feature engineering includes NDVI, LST, rainfall, temperature, humidity, evapotranspiration, soil moisture, VCI, TCI, VHI, SPI, SPEI, month and season encodings, lag features, rolling means, and wavelet decomposition features.

## Models

- LSTM
- CNN-LSTM
- BiLSTM
- GRU
- CNN grid-image model
- Wavelet + XGBoost
- PSO-optimized Wavelet XGBoost
- Wavelet + CNN/BiLSTM/GRU + XGBoost stacking ensemble

## Evaluation Protocols

| Protocol | Description |
|---|---|
| A | Strict chronological next-month forecasting |
| B | Paper-comparable random split |
| C | Same-month VHI estimation/reconstruction |
| D | Spatial grid-cell holdout |

## Results

| Protocol | Best model | R2 | RMSE | MAE | MAPE |
|---|---|---:|---:|---:|---:|
| Strict future forecasting | Proposed Wavelet + CNN/BiLSTM/GRU + XGBoost stacking | 0.8897 | 0.0581 | 0.0473 | 0.1092 |
| Paper-comparable random split | ExtraTrees random split | 0.6795 | 0.1367 | 0.0957 | 0.7114 |
| Same-month estimation | Wavelet-XGBoost VHI estimator | 0.9996 | 0.0050 | 0.0038 | 0.0137 |
| Spatial holdout | ExtraTrees unseen-grid holdout | 0.6634 | 0.1434 | 0.1063 | 0.6674 |

Base paper metrics are R2 `0.964`, RMSE `0.021`, and MAE `0.023`.

## Honest Conclusion

The project beats the base paper only under same-month VHI estimation/reconstruction. The strict future forecasting model is strong but does not yet beat the base paper metrics. This distinction must be preserved in reports, demos, and presentations.

## Recommended Next Work

1. Add longer time-series coverage from Google Earth Engine.
2. Add Sentinel-2 image patches and a CNN/ConvLSTM branch.
3. Add attention-based LSTM or a compact Transformer tuned with Optuna or PSO under chronological validation.
