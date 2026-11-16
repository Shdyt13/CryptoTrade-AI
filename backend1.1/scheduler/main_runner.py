import os
import sys
import time
import traceback
from datetime import datetime
import schedule

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bootstrap import ensure_initial_data
from config import COINS, TIMEFRAMES
from database import init_db
from evaluation import evaluator
from ingestion import fetcher
from predictors import hybrid_3d, hybrid_tcn_7d, lstm_1d


def run_safely(job_func, job_name: str):
    """Wrapper agar jika satu job error, scheduler TIDAK mati."""
    print(f"\n⏳ [{datetime.now().strftime('%H:%M:%S')}] Starting Job: {job_name}")
    try:
        job_func()
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Finished Job: {job_name}")
    except Exception as e:
        print(f"❌ ERROR in {job_name}: {e}")
        traceback.print_exc()


def job_ingest():
    run_safely(fetcher.ingest_all_coins, "Multi-Coin Ingestion Engine (ETH & SUI)")


def job_predict_1d():
    for coin in COINS.keys():
        run_safely(
            lambda c=coin: lstm_1d.train_and_predict(c),
            f"[{coin}] LSTM 1-Day Predictor",
        )


def job_predict_3d():
    for coin in COINS.keys():
        run_safely(
            lambda c=coin: hybrid_3d.train_and_predict(c),
            f"[{coin}] Hybrid LSTM+XGBoost 3-Day Predictor",
        )


def job_forecast_7d():
    for coin in COINS.keys():
        run_safely(
            lambda c=coin: hybrid_tcn_7d.train_and_predict(c),
            f"[{coin}] Hybrid TCN+XGBoost 7-Day Predictor",
        )


def job_evaluate():
    for coin in COINS.keys():
        for tf, cfg in TIMEFRAMES.items():
            run_safely(
                lambda t=tf, d=cfg["duration_minutes"], c=coin: evaluator.evaluate_predictions(
                    t, d, coin=c
                ),
                f"[{coin}] Evaluator {tf}",
            )


def run_scheduler():
    init_db()
    print("🚀 Multi-Coin Crypto Predictor (ETH & SUI | 1d LSTM, 3d Hybrid LSTM+XGB, 7d Hybrid TCN+XGB) System STARTED")
    print("   (Tekan Ctrl+C untuk menghentikan sistem)\n")

    print("⚡ Running initial startup jobs...")
    job_ingest()
    run_safely(ensure_initial_data, "Initial Real Model Bootstrap (ETH & SUI | 1d, 3d, 7d)")
    job_forecast_7d()
    job_predict_1d()
    job_predict_3d()
    job_evaluate()

    # Jadwal rutin
    schedule.every(30).seconds.do(job_ingest)
    schedule.every(1).hours.do(job_predict_1d)
    schedule.every(3).hours.do(job_predict_3d)
    schedule.every(6).hours.do(job_forecast_7d)
    schedule.every(15).minutes.do(job_evaluate)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 System Stopped by User.")


if __name__ == "__main__":
    run_scheduler()
