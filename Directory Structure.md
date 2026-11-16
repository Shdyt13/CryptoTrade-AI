# Directory Structure — Multi-Coin Crypto Predictor (ETH & SUI)

```text
ethereum-trend-predictor/
├── backend1.1/
│   ├── api.py                      # FastAPI REST endpoints & WebSocket (/ws)
│   ├── config.py                   # COINS (ETH, SUI) & TIMEFRAMES (1d, 3d, 7d)
│   ├── database.py                 # PostgreSQL schema, queries, RMSE/MAE/MAPE summary
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── decision/
│   │   ├── __init__.py
│   │   └── signal_engine.py        # Buy / Hold / Sell range decision engine
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── evaluator.py            # Evaluates matured 1d, 3d, 7d predictions
│   │   └── metrics.py              # RMSE, MAE, MAPE, Directional Accuracy
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── fetcher.py              # Indodax ticker & OHLCV fetcher for ETH & SUI
│   ├── predictors/
│   │   ├── __init__.py
│   │   ├── lstm_1d.py              # 1-Day Predictor: LSTM
│   │   └── hybrid_3d.py            # 3-Day Predictor: Hybrid LSTM + XGBoost (Residual Stacking)
│   ├── long_term/
│   │   ├── __init__.py
│   │   └── prophet_forecast.py     # 7-Day Predictor: Facebook Prophet
│   └── scheduler/
│       ├── __init__.py
│       └── main_runner.py          # Automated background scheduler
│
├── frontend_v1.1/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── src/
│       ├── App.jsx                 # Main app layout, ETH/SUI selector, 1d/3d/7d dashboard
│       ├── main.jsx
│       ├── index.css
│       ├── components/
│       │   ├── Analytics.jsx       # Actual vs Predicted chart & RMSE/MAE/MAPE charts
│       │   ├── ErrorBoundary.jsx   # UI crash recovery boundary
│       │   ├── PredictionCard.jsx  # Horizon prediction card + Buy/Hold/Sell progress bar
│       │   ├── PriceTicker.jsx     # Live market ticker for ETH/IDR & SUI/IDR
│       │   └── Sidebar.jsx         # Navigation & asset switcher
│       └── hooks/
│           └── useRealtimeData.js  # Shared WebSocket & REST hooks
│
├── docker-compose.yml
└── README.md
```
