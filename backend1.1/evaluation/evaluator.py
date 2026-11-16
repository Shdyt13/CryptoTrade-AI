import os
import sys
from datetime import datetime, timezone
import pytz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import COINS, TIMEFRAMES
from database import (
    evaluation_metrics_summary,
    get_daily_candles,
    mark_prediction_evaluated,
    pending_predictions,
    upsert_accuracy,
)
from evaluation.metrics import (
    calculate_direction_accuracy,
    calculate_mae,
    calculate_mape,
    calculate_rmse,
)

WIB_TZ = pytz.timezone("Asia/Jakarta")


def get_closed_daily_close(target_date_wib, coin: str = "ETH") -> float | None:
    """
    Mencari harga Close harian yang SUDAH LENGKAP / CLOSED (hari sudah berakhir)
    untuk tanggal target_date_wib dari tabel daily_candles.
    Jika tanggal tersebut adalah hari ini atau masa depan (belum tutup hari),
    maka belum ada harga Close aktual yang valid (return None).
    """
    today_wib = datetime.now(WIB_TZ).date()
    if target_date_wib >= today_wib:
        # Hari target belum selesai (candle harian belum close)
        return None

    candles = get_daily_candles(coin.upper(), limit=90)
    for c in candles:
        ts = c.get("timestamp")
        if ts is None:
            continue
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        c_date_wib = ts.astimezone(WIB_TZ).date()
        if c_date_wib == target_date_wib and c_date_wib < today_wib:
            return float(c["close"])
    return None


def evaluate_predictions(
    timeframe: str,
    duration_minutes: int | None = None,
    coin: str = "ETH",
):
    coin_code = coin.upper()
    horizon_days = TIMEFRAMES.get(timeframe, {}).get("horizon_days", 1)
    print(f"⚖️ [{coin_code}] Evaluating {timeframe} Daily Close Model (Horizon: {horizon_days}d)...")

    evaluated_count = 0
    now_utc = datetime.now(timezone.utc)
    today_wib = now_utc.astimezone(WIB_TZ).date()

    for prediction in pending_predictions(timeframe, coin=coin_code, limit=30):
        created_at = prediction["created_at"]
        if created_at.tzinfo is None:
            created_at = pytz.utc.localize(created_at)

        target_time = prediction.get("target_time")
        if target_time is None:
            continue
        if target_time.tzinfo is None:
            target_time = pytz.utc.localize(target_time)

        target_date_wib = target_time.astimezone(WIB_TZ).date()

        # ATURAN KETAT: Jika tanggal target >= hari ini (WIB), candle harian belum tutup (Close belum final)!
        if target_date_wib >= today_wib:
            continue

        actual_close = get_closed_daily_close(target_date_wib, coin=coin_code)
        if actual_close is None:
            print(
                f"   ⏳ [{coin_code} - {timeframe}] Data Close aktual untuk tanggal {target_date_wib} belum tersedia."
            )
            continue

        predicted_price = float(prediction["predicted_price"])
        previous_price = float(prediction["current_price_at_prediction"])

        mape = calculate_mape(actual_close, predicted_price)
        mae = calculate_mae(actual_close, predicted_price)
        rmse = calculate_rmse(actual_close, predicted_price)
        is_correct = calculate_direction_accuracy(
            previous_price, actual_close, predicted_price
        )

        mark_prediction_evaluated(
            prediction["id"],
            actual_close,
            mape,
            mae,
            rmse,
            bool(is_correct),
            now_utc,
        )
        print(
            f"   ✅ [{coin_code} - {timeframe}] Graded ({target_date_wib}): "
            f"Pred Close Rp {predicted_price:,.0f} vs Actual Close Rp {actual_close:,.0f} | "
            f"MAPE: {mape:.2f}% | MAE: Rp {mae:,.0f} | RMSE: Rp {rmse:,.0f}"
        )
        evaluated_count += 1

    summary = evaluation_metrics_summary(coin_code).get(timeframe)
    if summary and summary["samples"] > 0:
        upsert_accuracy(
            timeframe,
            now_utc,
            summary["mape"],
            summary["mae"],
            summary["rmse"],
            summary["direction_accuracy"],
            summary["samples"],
            coin=coin_code,
        )
        if evaluated_count > 0:
            print(
                f"📊 [{coin_code} - {timeframe}] Summary: MAPE {summary['mape']:.2f}% | "
                f"MAE Rp {summary['mae']:,.0f} | RMSE Rp {summary['rmse']:,.0f}"
            )


def evaluate_all():
    for coin_code in COINS.keys():
        for tf, cfg in TIMEFRAMES.items():
            evaluate_predictions(tf, cfg["duration_minutes"], coin=coin_code)


if __name__ == "__main__":
    evaluate_all()
