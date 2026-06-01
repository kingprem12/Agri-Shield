# Test Report

Validated on local machine on 2026-05-31.

## Backend

Command:

```bash
cd backend
.venv/bin/python scripts/run_etl.py --sample
.venv/bin/python scripts/train_model.py
.venv/bin/python scripts/train_deep_hybrid_benchmark.py --dataset-dir "../Data Sets" --limit-files 276 --max-grid-rows 10000 --epochs 8
.venv/bin/python scripts/generate_deep_hybrid_plots.py
.venv/bin/python -m pytest -q
```

Result: `5 passed`.

Model report generated at `backend/reports/model_metrics.json`.

Deep-hybrid benchmark generated at `backend/reports/deep_hybrid_benchmark.json`.

Best strict future-forecasting result: Proposed Wavelet + CNN/BiLSTM/GRU + XGBoost stacking ensemble, R² `0.8897`, RMSE `0.0581`, MAE `0.0473`.

Best same-month estimation result: Same-month Wavelet-XGBoost VHI estimation, R² `0.9996`, RMSE `0.0050`, MAE `0.0038`. This is paper-comparable estimation only, not future forecasting.

## Frontend

Command:

```bash
cd frontend
npm test
npm run build
```

Result: `1 passed`; production build completed successfully.

## API Smoke Test

Command:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/predict ...
```

Result:

```json
{"status":"ok","model_loaded":true,"environment":"local"}
```

Prediction returned `Moderate Drought` with risk score `53.77`.

AgriShield-X forecast smoke test returned `x_model_loaded: true` and a 3-month VHI forecast for Sindh.

`/benchmark` smoke test returned HTTP `200` with `deep_hybrid`, `gridcell_forecast`, `paper_style`, and `agrishield_x` reports.
