import os
import sys
from datetime import datetime, timedelta, timezone
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.layers import (
    Add,
    Conv1D,
    Dense,
    Dropout,
    GlobalAveragePooling1D,
    Input,
    LayerNormalization,
)
from tensorflow.keras.models import Model

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
HORIZON = 7        # 7 hari ke depan (prediksi Close 7 hari mendatang)
EPOCHS = 22
BATCH_SIZE = 16
MODEL_NAME = "Hybrid TCN + XGBoost (Residual Stacking OHLCV)"

META_FEATURE_COLS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "RSI",
    "EMA_7",
    "EMA_21",
    "MACD",
    "Volatility",
    "Daily_Range",
]


def build_tcn_base_model(lookback: int, n_features: int) -> Model:
    """
    Membangun arsitektur Temporal Convolutional Network (TCN) dengan
    Causal Dilated 1D Convolutions (dilation_rate = 1, 2, 4) dan Residual Skip Connections.
    """
    inputs = Input(shape=(lookback, n_features))

    # Proyeksi awal ke dimensi filter TCN (48 channel)
    x = Conv1D(filters=48, kernel_size=1, padding="same")(inputs)

    # Residual Dilated TCN Blocks (dilation 1, 2, 4)
    for dilation in (1, 2, 4):
        res = x
        conv1 = Conv1D(
            filters=48,
            kernel_size=3,
            padding="causal",
            dilation_rate=dilation,
            activation="relu",
        )(x)
        conv1 = Dropout(0.2)(conv1)
        conv2 = Conv1D(
            filters=48,
            kernel_size=3,
            padding="causal",
            dilation_rate=dilation,
            activation="relu",
        )(conv1)
        conv2 = Dropout(0.2)(conv2)
        x = Add()([res, conv2])
        x = LayerNormalization()(x)

    pooled = GlobalAveragePooling1D()(x)
    dense = Dense(24, activation="relu")(pooled)
    outputs = Dense(1)(dense)

    model = Model(inputs=inputs, outputs=outputs, name="TCN_Base_Learner_7d")
    model.compile(optimizer="adam", loss="mean_squared_error")
    return model


def add_daily_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Feature Engineering dari data daily (open, high, low, close, volume) untuk Meta-Learner XGBoost."""
    df = df.copy()

    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)

    df["EMA_7"] = df["close"].ewm(span=7, adjust=False).mean()
    df["EMA_21"] = df["close"].ewm(span=21, adjust=False).mean()

    ema_12 = df["close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema_12 - ema_26

    df["Volatility"] = df["close"].rolling(window=10).std().bfill().fillna(0.0)
    df["Daily_Range"] = (df["high"] - df["low"]) / df["close"].replace(0, 1.0)

    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def build_hybrid_tcn_sequences(
    df: pd.DataFrame,
    scaled_ohlcv: np.ndarray,
    scaled_target: np.ndarray,
    lookback: int = LOOKBACK,
    horizon: int = HORIZON,
):
    x_seq, y_target, tab_features, base_indices = [], [], [], []
    feature_matrix = df[META_FEATURE_COLS].values

    for i in range(len(df) - lookback - horizon + 1):
        end_idx = i + lookback - 1
        target_idx = end_idx + horizon
        x_seq.append(scaled_ohlcv[i : i + lookback, :])
        y_target.append(scaled_target[target_idx, 0])
        tab_features.append(feature_matrix[end_idx])
        base_indices.append(end_idx)

    return (
        np.array(x_seq),
        np.array(y_target),
        np.array(tab_features),
        base_indices,
    )


def seed_validation_history(
    coin: str,
    df: pd.DataFrame,
    target_scaler: MinMaxScaler,
    tcn_model: Model,
    xgb_meta: xgb.XGBRegressor,
    x_seq_all: np.ndarray,
    y_all: np.ndarray,
    tab_all: np.ndarray,
    base_indices: list[int],
    max_points: int = 14,
):
    """
    Mengevaluasi hasil prediksi model Hybrid TCN + XGBoost (7d) secara out-of-sample
    HANYA pada candle harian yang SUDAH TUTUP (is_closed = True, yaitu s/d kemarin).
    """
    if evaluated_count("7d", coin) >= 10:
        return

    n_samples = min(max_points, len(x_seq_all))
    if n_samples <= 0:
        return

    clear_evaluated_predictions("7d", coin)

    val_start = max(0, len(x_seq_all) - n_samples)
    indices = np.arange(val_start, len(x_seq_all), dtype=int)

    x_val_seq = x_seq_all[indices]
    tab_val = tab_all[indices]

    tcn_preds_scaled = tcn_model.predict(x_val_seq, verbose=0).flatten()
    tcn_preds_price = target_scaler.inverse_transform(tcn_preds_scaled.reshape(-1, 1)).flatten()

    meta_X_val = np.column_stack([tab_val, tcn_preds_price])
    residual_corrections = xgb_meta.predict(meta_X_val)

    hybrid_preds_price = tcn_preds_price + residual_corrections
    actuals_price = target_scaler.inverse_transform(y_all[indices].reshape(-1, 1)).flatten()

    mapes, maes, sq_errs, dir_hits = [], [], [], 0

    for idx_pos, seq_idx in enumerate(indices):
        df_base_idx = base_indices[seq_idx]
        df_target_idx = df_base_idx + HORIZON

        row_base = df.iloc[df_base_idx]
        curr_p = float(row_base["close"])
        act_p = float(actuals_price[idx_pos])
        pred_p = float(max(hybrid_preds_price[idx_pos], curr_p * 0.1))
        low_p = pred_p * 0.95
        high_p = pred_p * 1.05

        created_ts = pd.to_datetime(row_base["timestamp"]).to_pydatetime()
        if created_ts.tzinfo is None:
            created_ts = created_ts.replace(tzinfo=timezone.utc)
        target_ts = pd.to_datetime(df["timestamp"].iloc[df_target_idx]).to_pydatetime()
        if target_ts.tzinfo is None:
            target_ts = target_ts.replace(tzinfo=timezone.utc)

        change_pct = ((pred_p - curr_p) / curr_p) * 100.0 if curr_p else 0.0
        signal = "BULLISH TREND" if pred_p >= curr_p else "BEARISH TREND"
        rsi_val = float(row_base["RSI"])
        dec = generate_decision(
            curr_p,
            pred_p,
            change_pct,
            horizon_days=7,
            rsi=rsi_val,
            daily_df=df.iloc[: df_base_idx + 1],
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
                "timeframe": "7d",
                "predicted_price": pred_p,
                "current_price_at_prediction": curr_p,
                "signal": signal,
                "change_percent": change_pct,
                "lower_bound": low_p,
                "upper_bound": high_p,
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
                "last_close": curr_p,
                "last_volume": float(row_base["volume"]),
                "created_at": created_ts,
                "target_time": target_ts,
                "model": MODEL_NAME,
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
            "7d",
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
        f"⚡ [{coin_code}] Starting Hybrid TCN + XGBoost Residual Stacking (7-Day Horizon | Input: Closed Daily open, high, low, close, volume)..."
    )

    raw_df, validation = fetch_daily_ohlcv_validated(
        coin_code, limit=730, min_rows=LOOKBACK + HORIZON + 20, only_closed=True
    )
    if not validation["valid"] or raw_df is None:
        print(f"⛔ [{coin_code}] Prediksi 7d (Hybrid TCN + XGBoost) dibatalkan: {validation['message']}")
        return

    df = add_daily_indicators(raw_df)
    if len(df) < LOOKBACK + HORIZON + 10:
        print(f"⛔ [{coin_code}] Data daily setelah indikator belum mencukupi untuk 7d.")
        return

    ohlcv_matrix = df[REQUIRED_DAILY_VARIABLES].values
    close_target = df[["close"]].values

    feature_scaler = MinMaxScaler(feature_range=(0, 1))
    target_scaler = MinMaxScaler(feature_range=(0, 1))

    scaled_ohlcv = feature_scaler.fit_transform(ohlcv_matrix)
    scaled_target = target_scaler.fit_transform(close_target)

    x_seq_all, y_all, tab_all, base_indices = build_hybrid_tcn_sequences(
        df, scaled_ohlcv, scaled_target, LOOKBACK, HORIZON
    )

    n_features = len(REQUIRED_DAILY_VARIABLES)
    n_total = len(x_seq_all)
    val_count = min(14, max(2, n_total // 5))
    val_split = max(2, n_total - val_count)
    base_split = max(1, int(val_split * 0.72))

    # --- TAHAP 1: Base-Learner TCN (Temporal Convolutional Network pada Daily OHLCV) ---
    tcn_model = build_tcn_base_model(LOOKBACK, n_features)
    tcn_model.fit(
        x_seq_all[:base_split],
        y_all[:base_split],
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        verbose=0,
    )

    # --- TAHAP 2: Hitung Residual & Latih Meta-Learner XGBoost ---
    stack_seq = x_seq_all[:val_split]
    stack_y_scaled = y_all[:val_split]
    stack_tab = tab_all[:val_split]

    base_preds_scaled = tcn_model.predict(stack_seq, verbose=0).flatten()
    base_preds_price = target_scaler.inverse_transform(base_preds_scaled.reshape(-1, 1)).flatten()
    actual_stack_price = target_scaler.inverse_transform(stack_y_scaled.reshape(-1, 1)).flatten()

    residuals = actual_stack_price - base_preds_price
    meta_X_train = np.column_stack([stack_tab, base_preds_price])

    xgb_meta = xgb.XGBRegressor(
        n_estimators=130,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
    )
    xgb_meta.fit(meta_X_train, residuals)

    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    os.makedirs(models_dir, exist_ok=True)
    joblib.dump(xgb_meta, os.path.join(models_dir, f"hybrid_tcn_xgb_meta_{coin_code.lower()}_7d.pkl"))

    seed_validation_history(
        coin_code,
        df,
        target_scaler,
        tcn_model,
        xgb_meta,
        x_seq_all,
        y_all,
        tab_all,
        base_indices,
    )

    # --- TAHAP 3: Prediksi Close 7 Hari ke Depan dari Candle Closed Terakhir ---
    last_window = scaled_ohlcv[-LOOKBACK:].reshape(1, LOOKBACK, n_features)
    tcn_latest_scaled = tcn_model.predict(last_window, verbose=0)[0][0]
    tcn_latest_price = float(target_scaler.inverse_transform([[tcn_latest_scaled]])[0][0])

    latest_tab_features = df[META_FEATURE_COLS].iloc[-1].values
    meta_latest_input = np.append(latest_tab_features, tcn_latest_price).reshape(1, -1)
    residual_correction = float(xgb_meta.predict(meta_latest_input)[0])

    latest_row = df.iloc[-1]
    last_closed_ts = pd.to_datetime(latest_row["timestamp"]).to_pydatetime()
    if last_closed_ts.tzinfo is None:
        last_closed_ts = last_closed_ts.replace(tzinfo=timezone.utc)

    current_close = float(latest_row["close"])
    predicted_close = float(max(tcn_latest_price + residual_correction, current_close * 0.2))
    lower_bound = float(predicted_close * 0.95)
    upper_bound = float(predicted_close * 1.05)

    change_pct = ((predicted_close - current_close) / current_close) * 100.0
    signal = "BULLISH TREND" if predicted_close >= current_close else "BEARISH TREND"
    latest_rsi = float(latest_row["RSI"])
    decision_info = generate_decision(
        current_close, predicted_close, change_pct, horizon_days=7, rsi=latest_rsi, daily_df=df
    )

    now = datetime.now(timezone.utc)
    target_time = last_closed_ts + timedelta(days=HORIZON)

    print(
        f"💵 [{coin_code}] Last Closed Daily Candle ({latest_row.get('wib_date', last_closed_ts.date())}): "
        f"Close Rp {current_close:,.0f}"
    )
    print(
        f"🔮 [{coin_code}] Hybrid TCN+XGBoost 7d Predicted Close (Target {target_time.date()}): Rp {predicted_close:,.0f} "
        f"(Base TCN: Rp {tcn_latest_price:,.0f}, Residual XGB: {residual_correction:+,.0f})"
    )

    insert_prediction(
        {
            "coin": coin_code,
            "timeframe": "7d",
            "predicted_price": predicted_close,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
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
            "model": MODEL_NAME,
        },
        coin=coin_code,
    )
    print(f"💾 [{coin_code}] Hybrid TCN + XGBoost 7d Prediction saved!")


def train_and_predict_all():
    for coin_code in COINS.keys():
        train_and_predict(coin_code)


if __name__ == "__main__":
    train_and_predict_all()
