# Benchmark Comparison

Primary generated benchmark: `backend/reports/deep_hybrid_benchmark.json`.

Legacy AgriShield-X benchmark: `backend/reports/agrishield_x_benchmark.json`.

## Protocols

| Protocol | Meaning | Claim Rule |
|---|---|---|
| A strict chronological next-month | Train on past dates, test on future dates | Future forecasting |
| B paper-comparable random split | Random 70/30 split on real grid rows | Comparable to papers that use random splits |
| C same-month VHI estimation | Reconstruct current VHI from current indicators | Estimation only, not forecasting |
| D spatial grid-cell holdout | Hold out unseen grid cells | Spatial generalization check |

## Current Best Result

The current bounded full run used all 276 monthly CSV files, 36 sampled real grid cells, and 9,900 grid rows from 2001-01 through 2023-11.

Best model: Same-month Wavelet-XGBoost VHI estimation.

Best protocol: C same-month VHI estimation.

Base paper comparison:

| Metric | Base Paper | Current Best |
|---|---:|---:|
| R² | 0.964 | 0.9996 |
| RMSE | 0.021 | 0.0050 |
| MAE | 0.023 | 0.0038 |

Honest conclusion: this beats the base paper metrics only under paper-comparable same-month estimation. It must not be reported as a strict future-forecasting improvement.

## Models Included

- LSTM
- CNN-LSTM
- BiLSTM
- GRU
- Wavelet-XGBoost
- Optuna-optimized Wavelet-XGBoost
- PSO-optimized Wavelet-XGBoost
- ExtraTrees
- Proposed Wavelet + CNN/BiLSTM/GRU + XGBoost stacking ensemble
