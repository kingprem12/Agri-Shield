from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from sklearn.metrics import explained_variance_score, mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from torch import nn


@dataclass
class SequenceArtifacts:
    model: nn.Module
    scaler: StandardScaler
    history: list[dict[str, float]]
    train_indices: list[int]
    test_indices: list[int]


class SequenceRegressor(nn.Module):
    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        model_type: str = "lstm",
        num_layers: int = 1,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.model_type = model_type
        recurrent_dropout = dropout if num_layers > 1 else 0.0
        if model_type == "gru":
            self.encoder = nn.GRU(input_size, hidden_size, num_layers=num_layers, batch_first=True, dropout=recurrent_dropout)
            encoded_size = hidden_size
        elif model_type == "bilstm":
            self.encoder = nn.LSTM(
                input_size,
                hidden_size,
                num_layers=num_layers,
                batch_first=True,
                bidirectional=True,
                dropout=recurrent_dropout,
            )
            encoded_size = hidden_size * 2
        elif model_type == "cnn_lstm":
            self.conv = nn.Sequential(
                nn.Conv1d(input_size, hidden_size, kernel_size=3, padding=1),
                nn.BatchNorm1d(hidden_size),
                nn.ReLU(),
                nn.Dropout(dropout),
            )
            self.encoder = nn.LSTM(hidden_size, hidden_size, num_layers=num_layers, batch_first=True, dropout=recurrent_dropout)
            encoded_size = hidden_size
        else:
            self.encoder = nn.LSTM(input_size, hidden_size, num_layers=num_layers, batch_first=True, dropout=recurrent_dropout)
            encoded_size = hidden_size
        self.head = nn.Sequential(
            nn.Linear(encoded_size, max(16, hidden_size // 2)),
            nn.BatchNorm1d(max(16, hidden_size // 2)),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(max(16, hidden_size // 2), 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor, return_embedding: bool = False) -> torch.Tensor:
        encoded_input = x
        if self.model_type == "cnn_lstm":
            encoded_input = self.conv(x.transpose(1, 2)).transpose(1, 2)
        output, _ = self.encoder(encoded_input)
        embedding = output[:, -1, :]
        prediction = self.head(embedding).squeeze(-1)
        if return_embedding:
            return prediction, embedding
        return prediction


def make_sequences(values: np.ndarray, targets: np.ndarray, row_indices: np.ndarray, sequence_length: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x_rows, y_rows, indices = [], [], []
    for index in range(sequence_length, len(values)):
        x_rows.append(values[index - sequence_length : index])
        y_rows.append(targets[index])
        indices.append(row_indices[index])
    return np.asarray(x_rows, dtype=np.float32), np.asarray(y_rows, dtype=np.float32), np.asarray(indices, dtype=int)


def train_sequence_regressor(
    frame,
    features: list[str],
    target: str,
    model_type: str,
    sequence_length: int,
    hidden_size: int,
    learning_rate: float,
    max_epochs: int = 80,
    patience: int = 10,
) -> tuple[SequenceArtifacts, dict[str, float], np.ndarray, np.ndarray]:
    ordered = frame.sort_values("date").reset_index(drop=True)
    row_indices = ordered.index.to_numpy()
    split_row = int(len(ordered) * 0.8)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(ordered[features])
    x, y, sequence_indices = make_sequences(scaled, ordered[target].to_numpy(dtype=np.float32), row_indices, sequence_length)
    train_mask = sequence_indices < split_row
    test_mask = ~train_mask
    if train_mask.sum() < 8 or test_mask.sum() < 3:
        raise ValueError(f"Not enough samples for {model_type} seq={sequence_length}")
    x_train = torch.tensor(x[train_mask])
    y_train = torch.tensor(y[train_mask])
    x_test = torch.tensor(x[test_mask])
    y_test = y[test_mask]
    model = SequenceRegressor(len(features), hidden_size=hidden_size, model_type=model_type, dropout=0.2)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=4)
    loss_fn = nn.SmoothL1Loss()
    best_state = None
    best_loss = float("inf")
    stale_epochs = 0
    history = []
    torch.manual_seed(42)
    for epoch in range(max_epochs):
        model.train()
        optimizer.zero_grad()
        prediction = model(x_train)
        loss = loss_fn(prediction, y_train)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        model.eval()
        with torch.no_grad():
            validation_prediction = model(x_test)
            validation_loss = float(loss_fn(validation_prediction, torch.tensor(y_test)).item())
        scheduler.step(validation_loss)
        history.append({"epoch": epoch + 1, "train_loss": float(loss.item()), "validation_loss": validation_loss})
        if validation_loss < best_loss:
            best_loss = validation_loss
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
            stale_epochs = 0
        else:
            stale_epochs += 1
        if stale_epochs >= patience:
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        test_prediction = model(x_test).numpy()
    artifacts = SequenceArtifacts(
        model=model,
        scaler=scaler,
        history=history,
        train_indices=sequence_indices[train_mask].tolist(),
        test_indices=sequence_indices[test_mask].tolist(),
    )
    return artifacts, regression_metrics(y_test, test_prediction), y_test, test_prediction


def sequence_embeddings(artifact: SequenceArtifacts, frame, features: list[str], sequence_length: int) -> tuple[np.ndarray, np.ndarray]:
    ordered = frame.sort_values("date").reset_index(drop=True)
    scaled = artifact.scaler.transform(ordered[features])
    x, _, indices = make_sequences(
        scaled,
        np.zeros(len(ordered), dtype=np.float32),
        ordered.index.to_numpy(),
        sequence_length,
    )
    artifact.model.eval()
    with torch.no_grad():
        prediction, embedding = artifact.model(torch.tensor(x), return_embedding=True)
    return np.column_stack([prediction.numpy(), embedding.numpy()]), indices


def regression_metrics(y_true, y_pred) -> dict[str, float]:
    true = np.asarray(y_true, dtype=float)
    pred = np.clip(np.asarray(y_pred, dtype=float), 0, 1)
    return {
        "r2": float(r2_score(true, pred)),
        "rmse": float(mean_squared_error(true, pred) ** 0.5),
        "mae": float(mean_absolute_error(true, pred)),
        "mape": float(mean_absolute_percentage_error(np.clip(true, 0.01, 1), np.clip(pred, 0.01, 1))),
        "explained_variance": float(explained_variance_score(true, pred)),
    }
