import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import COINS, DEFAULT_COIN
from predictors.hybrid_tcn_7d import train_and_predict as run_hybrid_tcn_7d


def train_and_forecast(coin: str = DEFAULT_COIN):
    """Kompatibilitas pemanggilan lama: menjalankan Hybrid TCN + XGBoost untuk horizon 7 hari."""
    return run_hybrid_tcn_7d(coin)


def train_and_forecast_all():
    for coin_code in COINS.keys():
        run_hybrid_tcn_7d(coin_code)


if __name__ == "__main__":
    train_and_forecast_all()
