import os
import sys
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import COINS, REQUIRED_DAILY_VARIABLES
from database import evaluated_count, latest_prediction, latest_price
from ingestion.fetcher import (
    fetch_daily_ohlcv_validated,
    get_indodax_price,
    save_to_database,
)
from predictors.hybrid_3d import train_and_predict as run_hybrid_3d
from predictors.hybrid_tcn_7d import train_and_predict as run_hybrid_tcn_7d
from predictors.lstm_1d import train_and_predict as run_lstm_1d


def ensure_initial_data():
    """
    Memastikan data daily OHLCV riil dari Indodax (open, high, low, close, volume)
    tervalidasi, dan menjalankan model ML asli:
    - 1d: Multivariate LSTM
    - 3d: Hybrid LSTM + XGBoost
    - 7d: Hybrid TCN + XGBoost
    apabila evaluasi atau prediksi pada candle harian yang sudah close belum lengkap.
    """
    try:
        for coin in COINS.keys():
            if latest_price(coin) is None:
                p_data = get_indodax_price(coin)
                if p_data:
                    save_to_database(p_data, coin=coin)

            daily_df, validation = fetch_daily_ohlcv_validated(
                coin, limit=365, min_rows=20, only_closed=True
            )
            if not validation["valid"] or daily_df is None:
                print(
                    f"⛔ [Bootstrap {coin}] Prediksi belum dapat dilakukan karena variabel daily "
                    f"{REQUIRED_DAILY_VARIABLES} belum lengkap: {validation['reason']}"
                )
                continue

            if latest_prediction("1d", coin=coin) is None or evaluated_count("1d", coin=coin) < 10:
                run_lstm_1d(coin)

            if latest_prediction("3d", coin=coin) is None or evaluated_count("3d", coin=coin) < 10:
                run_hybrid_3d(coin)

            pred_7d = latest_prediction("7d", coin=coin)
            if (
                pred_7d is None
                or "TCN" not in str(pred_7d.get("model", ""))
                or evaluated_count("7d", coin=coin) < 10
            ):
                run_hybrid_tcn_7d(coin)
    except Exception as e:
        print(f"⚠️ Bootstrap warning: {e}")


def start_background_bootstrap():
    thread = threading.Thread(target=ensure_initial_data, daemon=True)
    thread.start()
