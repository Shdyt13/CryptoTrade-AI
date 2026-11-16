import os
import sys
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.layers import Dense, Dropout, LSTM
from tensorflow.keras.models import Sequential

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COINS, DEFAULT_COIN, REQUIRED_DAILY_VARIABLES
from database import (
    clear_evaluated_predictions,
    evaluated_count,
    insert_prediction,
    upsert_accuracy,
)
from decision.signal_engine import generate_decision
from evaluation.metrics import (
    calculate_direction_accuracy,
    calculate_mae,
    calculate_mape,
    calculate_rmse,
)
from ingestion.fetcher import fetch_daily_ohlcv_validated

LOOKBACK = 14      # 14 hari ke belakang (data daily OHLCV yang sudah close)
HORIZON = 1        # 1 hari ke depan (prediksi Close hari berikutnya)
EPOCHS = 20
BATCH_SIZE = 16


def compute_latest_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    val = rsi.iloc[-1]
    return float(val) if not pd.isna(val) else 50.0


def create_multivariate_sequences(
    scaled_features: np.ndarray,
    scaled_target: np.ndarray,
    lookback: int = LOOKBACK,
    horizon: int = HORIZON,
):
    """
    Membentuk sliding window X dari 5 variabel harian (open, high, low, close, volume)
    dan target y berupa harga close pada hari ke-(t + horizon).
    """
    data_x, data_y, base_indices = [], [], []
    for i in range(len(scaled_features) - lookback - horizon + 1):
        data_x.append(scaled_features[i : i + lookback, :])
        target_idx = i + lookback + horizon - 1
        data_y.append(scaled_target[target_idx, 0])
        base_indices.append(i + lookback - 1)
    return np.array(data_x), np.array(data_y), base_indices


def seed_validation_history(
    coin: str,
    df: pd.DataFrame,
    target_scaler: MinMaxScaler,
    model: Sequential,
    x_all: np.ndarray,
    y_all: np.ndarray,
    base_indices: list[int],
    max_points: int = 14,
):
    """
    Mengevaluasi hasil prediksi model Multivariate LSTM secara out-of-sample
    HANYA pada candle harian yang SUDAH TUTUP (is_closed = True, yaitu s/d kemarin).
    Candle hari ini yang sedang berjalan tidak dimasukkan ke evaluasi karena belum memiliki Close akhir.
    """
    if evaluated_count("1d", coin) >= 10:
        return

    n_samples = min(max_points, len(x_all))
    if n_samples <= 0:
        return

    clear_evaluated_predictions("1d", coin)

    val_start = max(0, len(x_all) - n_samples)
    indices = np.arange(val_start, len(x_all), dtype=int)

    x_val = x_all[indices]
    preds_scaled = model.predict(x_val, verbose=0)
    preds_price = target_scaler.inverse_transform(preds_scaled).flatten()
    actuals_price = target_scaler.inverse_transform(y_all[indices].reshape(-1, 1)).flatten()

    mapes, maes, sq_errs, dir_hits = [], [], [], 0

    for idx_pos, seq_idx in enumerate(indices):
        df_base_idx = base_indices[seq_idx]
        df_target_idx = df_base_idx + HORIZON

        row_base = df.iloc[df_base_idx]
        curr_p = float(row_base["close"])
        act_p = float(actuals_price[idx_pos])
        pred_p = float(max(preds_price[idx_pos], curr_p * 0.1))

        created_ts = pd.to_datetime(row_base["timestamp"]).to_pydatetime()
        if created_ts.tzinfo is None:
            created_ts = created_ts.replace(tzinfo=timezone.utc)
        target_ts = pd.to_datetime(df["timestamp"].iloc[df_target_idx]).to_pydatetime()
        if target_ts.tzinfo is None:
            target_ts = target_ts.replace(tzinfo=timezone.utc)

        change_pct = ((pred_p - curr_p) / curr_p) * 100.0 if curr_p else 0.0
        signal = "BULLISH" if pred_p >= curr_p else "BEARISH"
        dec = generate_decision(
            curr_p, pred_p, change_pct, horizon_days=1, daily_df=df.iloc[: df_base_idx + 1]
        )

        err_mape = calculate_mape(act_p, pred_p)
        err_mae = calculate_mae(act_p, pred_p)
        err_rmse = calculate_rmse(act_p, pred_p)
        dir_ok = bool(calculate_direction_accuracy(curr_p, act_p, pred_p))

        mapes.append(err_mape)
        maes.append(err_mae)
        sq_errs.append((act_p - pred_p) ** 2)
        dir_hits += int(dir_ok)

        insert_prediction(
            {
                "coin": coin,
                "timeframe": "1d",
                "predicted_price": pred_p,
                "current_price_at_prediction": curr_p,
                "signal": signal,
                "change_percent": change_pct,
                "buy_score": dec["buy_score"],
                "hold_score": dec["hold_score"],
                "sell_score": dec["sell_score"],
                "decision": dec["decision"],
                "auto_buy_price": dec["auto_buy_price"],
                "auto_sell_price": dec["auto_sell_price"],
                "stop_loss_price": dec["stop_loss_price"],
                "last_open": float(row_base["open"]),
                "last_high": float(row_base["high"]),
                "last_low": float(row_base["low"]),
                "last_close": float(row_base["close"]),
                "last_volume": float(row_base["volume"]),
                "created_at": created_ts,
                "target_time": target_ts,
                "model": "Multivariate LSTM (OHLCV Daily)",
                "actual_price": act_p,
                "error_mape": err_mape,
                "error_mae": err_mae,
                "error_rmse": err_rmse,
                "direction_correct": dir_ok,
                "evaluated": True,
                "evaluated_at": target_ts,
            },
            coin=coin,
        )

    if mapes:
        upsert_accuracy(
            "1d",
            datetime.now(timezone.utc),
            float(np.mean(mapes)),
            float(np.mean(maes)),
            float(np.sqrt(np.mean(sq_errs))),
            (dir_hits / len(mapes)) * 100.0,
            len(mapes),
            coin=coin,
        )


def train_and_predict(coin: str = DEFAULT_COIN):
    coin_code = coin.upper()
    print(
        f"🧠 [{coin_code}] Starting Multivariate Daily LSTM Engine (1-Day Horizon | Input: Closed Daily open, high, low, close, volume)..."
    )

    # Ambil HANYA candle daily yang sudah selesai/closed (only_closed=True)
    df, validation = fetch_daily_ohlcv_validated(
        coin_code, limit=365, min_rows=LOOKBACK + HORIZON + 10, only_closed=True
    )
    if not validation["valid"] or df is None:
        print(f"⛔ [{coin_code}] Prediksi 1d dibatalkan: {validation['message']}")
        return

    feature_matrix = df[REQUIRED_DAILY_VARIABLES].values
    close_target = df[["close"]].values

    feature_scaler = MinMaxScaler(feature_range=(0, 1))
    target_scaler = MinMaxScaler(feature_range=(0, 1))

    scaled_features = feature_scaler.fit_transform(feature_matrix)
    scaled_target = target_scaler.fit_transform(close_target)

    x_all, y_all, base_indices = create_multivariate_sequences(
        scaled_features, scaled_target, LOOKBACK, HORIZON
    )

    n_features = len(REQUIRED_DAILY_VARIABLES)
    # Latih model pada data sebelum 14 hari terakhir agar 14 hari terakhir murni out-of-sample
    val_count = min(14, max(1, len(x_all) // 5))
    split_idx = max(1, len(x_all) - val_count)
    x_train, y_train = x_all[:split_idx], y_all[:split_idx]

    model = Sequential(
        [
            LSTM(units=64, return_sequences=True, input_shape=(LOOKBACK, n_features)),
            Dropout(0.2),
            LSTM(units=48),
            Dropout(0.2),
            Dense(units=24, activation="relu"),
            Dense(units=1),
        ]
    )
    model.compile(optimizer="adam", loss="mean_squared_error")
    model.fit(x_train, y_train, epochs=EPOCHS, batch_size=BATCH_SIZE, verbose=0)

    seed_validation_history(coin_code, df, target_scaler, model, x_all, y_all, base_indices)

    # Lanjutkan fine-tune singkat pada seluruh candle yang sudah closed untuk memprediksi 1 hari ke depan
    if len(x_all) > split_idx:
        model.fit(x_all[split_idx:], y_all[split_idx:], epochs=5, batch_size=BATCH_SIZE, verbose=0)

    last_window = scaled_features[-LOOKBACK:].reshape(1, LOOKBACK, n_features)
    predicted_scaled = model.predict(last_window, verbose=0)
    predicted_close = float(target_scaler.inverse_transform(predicted_scaled)[0][0])

    latest_row = df.iloc[-1]
    last_closed_ts = pd.to_datetime(latest_row["timestamp"]).to_pydatetime()
    if last_closed_ts.tzinfo is None:
        last_closed_ts = last_closed_ts.replace(tzinfo=timezone.utc)

    current_close = float(latest_row["close"])
    predicted_close = float(max(predicted_close, current_close * 0.1))

    change_pct = ((predicted_close - current_close) / current_close) * 100.0
    signal = "BULLISH" if predicted_close >= current_close else "BEARISH"
    latest_rsi = compute_latest_rsi(df["close"])
    decision_info = generate_decision(
        current_close, predicted_close, change_pct, horizon_days=1, rsi=latest_rsi, daily_df=df
    )

    now = datetime.now(timezone.utc)
    # Target waktu prediksi 1d adalah 1 hari setelah candle daily terakhir yang sudah close (misal: 14 Nov -> target 15 Nov)
    target_time = last_closed_ts + timedelta(days=HORIZON)

    print(
        f"💵 [{coin_code}] Last Closed Daily Candle ({latest_row.get('wib_date', last_closed_ts.date())}): "
        f"Close Rp {current_close:,.0f}"
    )
    print(
        f"🔮 [{coin_code}] Predicted 1d Close (Target {target_time.date()}): "
        f"Rp {predicted_close:,.0f} ({change_pct:+.2f}%)"
    )

    insert_prediction(
        {
            "coin": coin_code,
            "timeframe": "1d",
            "predicted_price": predicted_close,
            "current_price_at_prediction": current_close,
            "signal": signal,
            "change_percent": float(change_pct),
            "buy_score": decision_info["buy_score"],
            "hold_score": decision_info["hold_score"],
            "sell_score": decision_info["sell_score"],
            "decision": decision_info["decision"],
            "auto_buy_price": decision_info["auto_buy_price"],
            "auto_sell_price": decision_info["auto_sell_price"],
            "stop_loss_price": decision_info["stop_loss_price"],
            "last_open": float(latest_row["open"]),
            "last_high": float(latest_row["high"]),
            "last_low": float(latest_row["low"]),
            "last_close": current_close,
            "last_volume": float(latest_row["volume"]),
            "created_at": now,
            "target_time": target_time,
            "model": "Multivariate LSTM (OHLCV Daily)",
        },
        coin=coin_code,
    )
    print(f"💾 [{coin_code}] Multivariate LSTM 1d Prediction saved!")


def train_and_predict_all():
    for coin_code in COINS.keys():
        train_and_predict(coin_code)


if __name__ == "__main__":
    train_and_predict_all()
