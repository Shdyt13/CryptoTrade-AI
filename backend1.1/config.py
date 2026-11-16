COINS = {
    "ETH": "ETH/IDR",
    "SUI": "SUI/IDR",
}

DEFAULT_COIN = "ETH"
SYMBOL = COINS[DEFAULT_COIN]

# Kelima variabel wajib pada data harian (daily) agar prediksi dapat dilakukan
REQUIRED_DAILY_VARIABLES = ["open", "high", "low", "close", "volume"]

TIMEFRAMES = {
    "1d": {
        "label": "1 Hari (1d)",
        "candle": "1d",
        "limit": 365,
        "horizon_days": 1,
        "duration_minutes": 1440,
        "min_daily_rows": 30,
        "model_name": "Multivariate LSTM (OHLCV Daily)",
    },
    "3d": {
        "label": "3 Hari (3d)",
        "candle": "1d",
        "limit": 500,
        "horizon_days": 3,
        "duration_minutes": 4320,
        "min_daily_rows": 45,
        "model_name": "Hybrid LSTM + XGBoost (Residual Stacking OHLCV)",
    },
    "7d": {
        "label": "7 Hari (7d)",
        "candle": "1d",
        "limit": 730,
        "horizon_days": 7,
        "duration_minutes": 10080,
        "min_daily_rows": 45,
        "model_name": "Hybrid TCN + XGBoost (Residual Stacking OHLCV)",
    },
}
