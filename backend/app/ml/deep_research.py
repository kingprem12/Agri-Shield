from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import explained_variance_score, mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from torch import nn
from xgboost import XGBRegressor

from app.ml.x_features import engineer_research_features, read_custom_csvs


SEQUENCE_COLUMNS = [
    "ndvi",
    "lst",
    "rainfall",
    "temperature",
    "humidity",
    "solar_radiation",
    "wind_speed",
    "soil_moisture",
    "vci",
    "tci",
    "spi",
    "spei",
    "mndwi",
    "vhi_lag_1",
    "vhi_roll_3",
    "ndvi_wavelet_approx",
    "lst_wavelet_approx",
    "rainfall_wavelet_approx",
]


class VhiLSTM(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 48):
        super().__init__()
        self.lstm = nn.LSTM(input_size=input_size, hidden_size=hidden_size, batch_first=True)
        self.head = nn.Sequential(nn.Linear(hidden_size, 32), nn.ReLU(), nn.Linear(32, 1), nn.Sigmoid())

    def forward(self, x):
        output, _ = self.lstm(x)
        return self.head(output[:, -1, :]).squeeze(-1) * 100


class VhiGridCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.head = nn.Sequential(nn.Flatten(), nn.Linear(32 * 4 * 4, 64), nn.ReLU(), nn.Linear(64, 1), nn.Sigmoid())

    def forward(self, x):
        return self.head(self.encoder(x)).squeeze(-1) * 100


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    clipped = np.clip(y_pred, 0, 100)
    return {
        "r2": float(r2_score(y_true, clipped)),
        "rmse": float(mean_squared_error(y_true, clipped) ** 0.5),
        "mae": float(mean_absolute_error(y_true, clipped)),
        "mape": float(mean_absolute_percentage_error(np.clip(y_true, 1, 100), np.clip(clipped, 1, 100))),
        "explained_variance": float(explained_variance_score(y_true, clipped)),
        "accuracy_within_10_vhi": float(np.mean(np.abs(y_true - clipped) <= 10)),
    }


def _train_torch_model(model: nn.Module, x_train: torch.Tensor, y_train: torch.Tensor, epochs: int = 80) -> nn.Module:
    torch.manual_seed(42)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.003, weight_decay=1e-4)
    loss_fn = nn.SmoothL1Loss()
    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = loss_fn(model(x_train), y_train)
        loss.backward()
        optimizer.step()
    return model.eval()


def _monthly_features(raw: pd.DataFrame) -> pd.DataFrame:
    features = engineer_research_features(raw)
    numeric = features.select_dtypes(include=["number"]).columns
    monthly = (
        features.assign(grid_id="sindh_monthly")
        .groupby(["region", "grid_id", "date"], as_index=False)[numeric]
        .mean()
        .sort_values("date")
    )
    return engineer_research_features(monthly).sort_values("date").reset_index(drop=True)


def _sequence_dataset(monthly: pd.DataFrame, sequence_length: int = 6):
    scaler = StandardScaler()
    values = scaler.fit_transform(monthly[SEQUENCE_COLUMNS])
    targets = monthly["target_vhi_next"].to_numpy(dtype=np.float32)
    x, y, rows = [], [], []
    for index in range(sequence_length, len(monthly)):
        x.append(values[index - sequence_length : index])
        y.append(targets[index])
        rows.append(monthly.iloc[index])
    return np.asarray(x, dtype=np.float32), np.asarray(y, dtype=np.float32), pd.DataFrame(rows), scaler


def _parse_coords(frame: pd.DataFrame) -> pd.DataFrame:
    parsed = frame[".geo"].apply(json.loads)
    frame = frame.copy()
    frame["longitude"] = parsed.apply(lambda geo: geo["coordinates"][0])
    frame["latitude"] = parsed.apply(lambda geo: geo["coordinates"][1])
    return frame


def _grid_images(paths: list[Path]) -> tuple[np.ndarray, pd.DataFrame]:
    images = []
    summaries = []
    for path in paths:
        frame = _parse_coords(pd.read_csv(path))
        frame["date"] = pd.to_datetime(str(frame["date"].iloc[0]).replace("_", "-"))
        summaries.append(
            {
                "date": frame["date"].iloc[0],
                "ndvi_mean": frame["NDVI"].mean(),
                "lst_mean": frame["LST"].mean(),
                "rainfall_mean": frame["Precipitation"].mean(),
            }
        )
        channels = []
        for column in ["NDVI", "LST", "Precipitation"]:
            pivot = frame.pivot_table(index="latitude", columns="longitude", values=column, aggfunc="mean").sort_index(ascending=False)
            values = pivot.to_numpy(dtype=np.float32)
            fill = np.nanmedian(values)
            values = np.nan_to_num(values, nan=fill)
            low, high = np.percentile(values, [2, 98])
            values = np.clip((values - low) / max(high - low, 1e-6), 0, 1)
            channels.append(values)
        images.append(np.stack(channels, axis=0))
    return np.asarray(images, dtype=np.float32), pd.DataFrame(summaries).sort_values("date").reset_index(drop=True)


def train_three_research_models(csv_paths: list[Path], output_dir: Path, report_path: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    csv_paths = sorted(csv_paths, key=lambda path: path.name)
    raw = read_custom_csvs(csv_paths)
    monthly = _monthly_features(raw)
    x_seq, y_seq, seq_rows, scaler = _sequence_dataset(monthly)
    split = max(8, int(len(y_seq) * 0.8))
    x_train, x_test = x_seq[:split], x_seq[split:]
    y_train, y_test = y_seq[:split], y_seq[split:]

    lstm = _train_torch_model(VhiLSTM(input_size=x_seq.shape[-1]), torch.tensor(x_train), torch.tensor(y_train))
    with torch.no_grad():
        lstm_train_pred = lstm(torch.tensor(x_train)).numpy()
        lstm_pred = lstm(torch.tensor(x_test)).numpy()

    images, image_summary = _grid_images(csv_paths)
    image_monthly = image_summary.merge(monthly[["date", "target_vhi_next"]], on="date", how="inner")
    aligned_count = len(image_monthly)
    images = images[-aligned_count:]
    y_img = image_monthly["target_vhi_next"].to_numpy(dtype=np.float32)
    img_split = max(8, int(len(y_img) * 0.8))
    cnn = _train_torch_model(VhiGridCNN(), torch.tensor(images[:img_split]), torch.tensor(y_img[:img_split]), epochs=70)
    with torch.no_grad():
        cnn_train_pred = cnn(torch.tensor(images[:img_split])).numpy()
        cnn_pred = cnn(torch.tensor(images[img_split:])).numpy()

    feature_xgb = XGBRegressor(n_estimators=180, max_depth=3, learning_rate=0.04, objective="reg:squarederror", random_state=74)
    feature_xgb.fit(seq_rows[SEQUENCE_COLUMNS].iloc[:split], y_train)
    feature_train_pred = feature_xgb.predict(seq_rows[SEQUENCE_COLUMNS].iloc[:split])
    feature_pred = feature_xgb.predict(seq_rows[SEQUENCE_COLUMNS].iloc[split:])
    persistence_train_pred = seq_rows["vhi_lag_1"].iloc[:split].to_numpy()
    persistence_pred = seq_rows["vhi_lag_1"].iloc[split:].to_numpy()

    meta_train_len = min(len(lstm_train_pred), len(cnn_train_pred))
    meta_test_len = min(len(lstm_pred), len(cnn_pred))
    engineered_train = seq_rows[SEQUENCE_COLUMNS].iloc[:split].tail(meta_train_len).to_numpy()
    engineered_test = seq_rows[SEQUENCE_COLUMNS].iloc[split:].head(meta_test_len).to_numpy()
    meta_x_train = np.column_stack([
        lstm_train_pred[-meta_train_len:],
        cnn_train_pred[-meta_train_len:],
        feature_train_pred[-meta_train_len:],
        persistence_train_pred[-meta_train_len:],
        engineered_train,
    ])
    meta_y_train = y_train[-meta_train_len:]
    meta_x_test = np.column_stack([
        lstm_pred[:meta_test_len],
        cnn_pred[:meta_test_len],
        feature_pred[:meta_test_len],
        persistence_pred[:meta_test_len],
        engineered_test,
    ])
    meta_y_test = y_test[:meta_test_len]
    hybrid = XGBRegressor(n_estimators=120, max_depth=3, learning_rate=0.05, objective="reg:squarederror", random_state=84)
    hybrid.fit(meta_x_train, meta_y_train)
    hybrid_pred = hybrid.predict(meta_x_test)

    torch.save({"state_dict": lstm.state_dict(), "input_size": x_seq.shape[-1], "features": SEQUENCE_COLUMNS}, output_dir / "vhi_lstm.pt")
    torch.save({"state_dict": cnn.state_dict(), "channels": ["NDVI", "LST", "Precipitation"]}, output_dir / "vhi_grid_cnn.pt")
    joblib.dump(
        {
            "model": hybrid,
            "feature_xgb": feature_xgb,
            "features": ["lstm_prediction", "cnn_prediction", "feature_xgb_prediction", "persistence_prediction"] + SEQUENCE_COLUMNS,
        },
        output_dir / "vhi_hybrid_xgb_meta.joblib",
    )
    joblib.dump({"sequence_scaler": scaler}, output_dir / "research_preprocessors.joblib")

    report = {
        "project": "AgriShield-X",
        "target": "next-month VHI",
        "trained_models": [
            {"model": "Real PyTorch LSTM", **_metrics(y_test, lstm_pred)},
            {"model": "Real PyTorch CNN grid image model", **_metrics(y_img[img_split:], cnn_pred)},
            {"model": "Engineered feature XGBoost support model", **_metrics(y_test, feature_pred)},
            {"model": "Persistence support model", **_metrics(y_test, persistence_pred)},
            {"model": "Advanced Hybrid LSTM + CNN + XGBoost meta learner", **_metrics(meta_y_test, hybrid_pred)},
        ],
        "base_paper": {
            "status": "pending_exact_extraction",
            "note": "Do not claim improvement until exact metrics are extracted from the paper and matched to the same target/horizon.",
        },
        "samples": {"monthly_rows": len(monthly), "sequence_samples": len(y_seq), "image_samples": len(y_img), "test_samples": int(meta_test_len)},
    }
    report_path.write_text(json.dumps(report, indent=2))
    return report
