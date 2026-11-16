import math
from typing import Any
import numpy as np
import pandas as pd

REQUIRED_VARIABLES = ["open", "high", "low", "close", "volume"]


def validate_daily_ohlcv(df: pd.DataFrame | None, min_rows: int = 15) -> dict[str, Any]:
    """
    Memvalidasi bahwa data harian (daily) memiliki kelima variabel wajib:
    open, high, low, close, volume.
    Jika ada variabel yang belum tersedia atau bernilai kosong/NaN pada baris terbaru,
    prediksi TIDAK dapat dilakukan.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        msg = "Data harian (daily) belum tersedia. Prediksi belum dapat dilakukan."
        return {
            "valid": False,
            "variables_complete": False,
            "required_variables": REQUIRED_VARIABLES,
            "missing_variables": REQUIRED_VARIABLES,
            "available_rows": 0,
            "row_count": 0,
            "min_rows": min_rows,
            "message": msg,
            "reason": msg,
        }

    missing = [col for col in REQUIRED_VARIABLES if col not in df.columns]
    if missing:
        msg = f"Variabel wajib belum lengkap ({', '.join(missing)}). Prediksi belum dapat dilakukan."
        return {
            "valid": False,
            "variables_complete": False,
            "required_variables": REQUIRED_VARIABLES,
            "missing_variables": missing,
            "available_rows": len(df),
            "row_count": len(df),
            "min_rows": min_rows,
            "message": msg,
            "reason": msg,
        }

    # Cek apakah ada variabel yang seluruhnya kosong atau baris terakhirnya tidak memiliki nilai valid
    incomplete_vars = []
    latest_row = df.iloc[-1]
    for col in REQUIRED_VARIABLES:
        val = latest_row[col]
        if pd.isna(val) or val is None:
            incomplete_vars.append(col)
        elif col in ("open", "high", "low", "close") and float(val) <= 0:
            incomplete_vars.append(col)
        elif col == "volume" and float(val) < 0:
            incomplete_vars.append(col)

    if incomplete_vars:
        msg = (
            f"Data harian terbaru belum memiliki nilai valid untuk variabel: "
            f"{', '.join(incomplete_vars)}. Prediksi belum dapat dilakukan."
        )
        return {
            "valid": False,
            "variables_complete": False,
            "required_variables": REQUIRED_VARIABLES,
            "missing_variables": incomplete_vars,
            "available_rows": len(df),
            "row_count": len(df),
            "min_rows": min_rows,
            "message": msg,
            "reason": msg,
        }

    clean_df = df.dropna(subset=REQUIRED_VARIABLES)
    if len(clean_df) < min_rows:
        msg = (
            f"Jumlah data harian lengkap (open, high, low, close, volume) baru {len(clean_df)} hari "
            f"(minimal {min_rows} hari). Prediksi belum dapat dilakukan."
        )
        return {
            "valid": False,
            "variables_complete": False,
            "required_variables": REQUIRED_VARIABLES,
            "missing_variables": [],
            "available_rows": len(clean_df),
            "row_count": len(clean_df),
            "min_rows": min_rows,
            "message": msg,
            "reason": msg,
        }

    msg = "Seluruh variabel harian (open, high, low, close, volume) lengkap dan valid."
    return {
        "valid": True,
        "variables_complete": True,
        "required_variables": REQUIRED_VARIABLES,
        "missing_variables": [],
        "available_rows": len(clean_df),
        "row_count": len(clean_df),
        "min_rows": min_rows,
        "latest_ohlcv": {
            "open": float(latest_row["open"]),
            "high": float(latest_row["high"]),
            "low": float(latest_row["low"]),
            "close": float(latest_row["close"]),
            "volume": float(latest_row["volume"]),
        },
        "message": msg,
        "reason": msg,
    }


def generate_decision(
    current_price: float,
    predicted_price: float,
    change_pct: float | None = None,
    horizon_days: int = 1,
    rsi: float | None = None,
    daily_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """
    Menghasilkan saran keputusan BUY / HOLD / SELL beserta persentase rentang keputusan
    (misal: Sell 70%, Hold 20%, Buy 10%), prediksi Close, serta rekomendasi
    nilai Auto Buy, Auto Sell, dan Stop Loss berdasarkan pergerakan harian OHLCV.
    """
    if change_pct is None:
        if current_price and current_price > 0:
            change_pct = ((predicted_price - current_price) / current_price) * 100.0
        else:
            change_pct = 0.0

    scale = max(math.sqrt(max(horizon_days, 1)), 1.0)
    normalized_change = change_pct / scale

    rsi_bias = 0.0
    if rsi is not None and not math.isnan(rsi):
        if rsi < 35:
            rsi_bias = (35 - rsi) * 0.03
        elif rsi > 65:
            rsi_bias = -(rsi - 65) * 0.03

    score = max(-4.0, min(4.0, normalized_change + rsi_bias))

    logit_buy = 0.42 * score
    logit_sell = -0.42 * score
    logit_hold = 0.35 - 0.22 * abs(score)

    max_logit = max(logit_buy, logit_sell, logit_hold)
    exp_buy = math.exp(logit_buy - max_logit)
    exp_sell = math.exp(logit_sell - max_logit)
    exp_hold = math.exp(logit_hold - max_logit)
    total = exp_buy + exp_sell + exp_hold

    raw_buy = (exp_buy / total) * 100.0
    raw_sell = (exp_sell / total) * 100.0
    raw_hold = (exp_hold / total) * 100.0

    buy_pct = max(5, round(raw_buy))
    sell_pct = max(5, round(raw_sell))
    hold_pct = max(5, 100 - buy_pct - sell_pct)

    diff = 100 - (buy_pct + sell_pct + hold_pct)
    if diff != 0:
        if score > 0.3:
            buy_pct += diff
        elif score < -0.3:
            sell_pct += diff
        else:
            hold_pct += diff

    scores = {"BUY": buy_pct, "HOLD": hold_pct, "SELL": sell_pct}
    decision = max(scores, key=scores.get)

    # Hitung volatilitas/rentang rata-rata harian (ATR%) dari data OHLCV jika tersedia
    avg_daily_range_pct = 0.025  # default 2.5%
    if (
        daily_df is not None
        and isinstance(daily_df, pd.DataFrame)
        and all(c in daily_df.columns for c in ("high", "low", "close"))
        and len(daily_df) >= 5
    ):
        recent = daily_df.tail(14)
        ranges = (recent["high"] - recent["low"]) / recent["close"].replace(0, np.nan)
        mean_r = float(ranges.mean())
        if not math.isnan(mean_r) and mean_r > 0:
            avg_daily_range_pct = max(0.01, min(0.12, mean_r))

    horizon_buffer = avg_daily_range_pct * math.sqrt(max(horizon_days, 1)) * 0.55

    # Strategi penetapan nilai Auto Buy & Auto Sell berdasarkan prediksi Close
    if predicted_price >= current_price:
        # Tren naik (Bullish):
        # Auto Buy dipasang sedikit di bawah harga saat ini (entry on dip / support harian)
        auto_buy_price = current_price * (1.0 - min(avg_daily_range_pct * 0.45, 0.03))
        # Auto Sell dipasang pada target prediksi Close atau puncak resistance proyeksi
        auto_sell_price = max(predicted_price, current_price * (1.0 + horizon_buffer))
        stop_loss_price = auto_buy_price * (1.0 - max(avg_daily_range_pct * 0.8, 0.02))
    else:
        # Tren turun (Bearish):
        # Auto Sell dipasang dekat harga saat ini / pantulan resistance kecil untuk mengamankan profit/cut risk
        auto_sell_price = current_price * (1.0 + min(avg_daily_range_pct * 0.35, 0.025))
        # Auto Buy dipasang di area diskon dekat prediksi Close bawah (buyback target)
        auto_buy_price = min(predicted_price, current_price * (1.0 - horizon_buffer))
        stop_loss_price = auto_buy_price * (1.0 - max(avg_daily_range_pct * 0.8, 0.025))

    return {
        "decision": decision,
        "buy_score": float(buy_pct),
        "hold_score": float(hold_pct),
        "sell_score": float(sell_pct),
        "auto_buy_price": round(float(auto_buy_price), 2),
        "auto_sell_price": round(float(auto_sell_price), 2),
        "stop_loss_price": round(float(stop_loss_price), 2),
    }
