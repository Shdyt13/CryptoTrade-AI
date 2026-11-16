import asyncio
import json
import os
import sys
from datetime import date, datetime
import pandas as pd
import pytz

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bootstrap import start_background_bootstrap
from config import COINS, DEFAULT_COIN, REQUIRED_DAILY_VARIABLES, TIMEFRAMES
from database import (
    evaluation_metrics_summary,
    get_daily_candles,
    init_db,
    latest_prediction,
    latest_price,
    prediction_history,
)
from decision.signal_engine import generate_decision, validate_daily_ohlcv
from ingestion.fetcher import WIB_TZ, fetch_daily_ohlcv_validated


raw_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost,http://localhost:80,http://localhost:5173,http://127.0.0.1,http://127.0.0.1:80,http://127.0.0.1:5173",
)
allowed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app = FastAPI(title="Multi-Coin Crypto Trend Predictor API (ETH & SUI)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def serialize(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize(item) for item in value]
    return value


def get_coin_candles_and_validation(coin: str, limit: int = 60, min_rows: int = 14) -> dict:
    """
    Mengambil data candle harian (open, high, low, close, volume) yang SUDAH LENGKAP / CLOSED
    (tanggal < hari ini WIB) untuk input model & grafik, serta memisahkan candle hari ini
    yang sedang berjalan (belum memiliki Close akhir hari).
    """
    coin_code = coin.upper()
    today_wib = datetime.now(WIB_TZ).date()
    rows = get_daily_candles(coin_code, limit=limit + 5)

    if len(rows) < min_rows + 1:
        fetch_daily_ohlcv_validated(
            coin_code, limit=max(limit, 120), min_rows=min_rows, only_closed=True
        )
        rows = get_daily_candles(coin_code, limit=limit + 5)

    closed_rows = []
    running_candle = None
    for r in rows:
        item = dict(r)
        ts = item.get("timestamp")
        if isinstance(ts, str):
            ts_dt = datetime.fromisoformat(ts)
        else:
            ts_dt = ts
        if ts_dt.tzinfo is None:
            ts_dt = pytz.utc.localize(ts_dt)
        wib_date = ts_dt.astimezone(WIB_TZ).date()
        item["wib_date"] = wib_date.isoformat()
        item["is_closed"] = wib_date < today_wib
        if wib_date < today_wib:
            closed_rows.append(item)
        elif wib_date == today_wib:
            running_candle = item

    closed_rows = closed_rows[-limit:]
    df_closed = pd.DataFrame(closed_rows) if closed_rows else None
    val = validate_daily_ohlcv(df_closed, min_rows=min_rows)
    if closed_rows:
        val["last_closed_date"] = closed_rows[-1]["wib_date"]
    val["running_date"] = today_wib.isoformat()
    val["running_candle_status"] = (
        f"Candle tanggal {today_wib.isoformat()} masih berjalan (belum memiliki nilai Close harian akhir)."
    )

    return {
        "coin": coin_code,
        "required_variables": REQUIRED_DAILY_VARIABLES,
        "validation": val,
        "candles": closed_rows,
        "running_candle": running_candle,
    }


def enrich_prediction(
    pred: dict | None,
    horizon_days: int = 1,
    daily_df: pd.DataFrame | None = None,
    validation: dict | None = None,
) -> dict | None:
    """
    Pastikan setiap prediksi memiliki:
    - decision & buy/hold/sell score
    - auto_buy_price, auto_sell_price, stop_loss_price
    - last_open, last_high, last_low, last_close, last_volume
    - data_validation status
    """
    if not pred:
        return None
    item = dict(pred)
    curr_p = float(item.get("current_price_at_prediction") or item.get("last_close") or 0.0)
    pred_p = float(item.get("predicted_price") or 0.0)

    buy_s = item.get("buy_score") or 0.0
    hold_s = item.get("hold_score") or 0.0
    sell_s = item.get("sell_score") or 0.0
    needs_dec = (
        (buy_s + hold_s + sell_s) <= 0
        or item.get("auto_buy_price") is None
        or item.get("auto_sell_price") is None
        or item.get("stop_loss_price") is None
    )
    if needs_dec and curr_p > 0 and pred_p > 0:
        dec = generate_decision(
            curr_p,
            pred_p,
            item.get("change_percent"),
            horizon_days=horizon_days,
            daily_df=daily_df,
        )
        if (buy_s + hold_s + sell_s) <= 0:
            item["decision"] = dec["decision"]
            item["buy_score"] = dec["buy_score"]
            item["hold_score"] = dec["hold_score"]
            item["sell_score"] = dec["sell_score"]
        if item.get("auto_buy_price") is None:
            item["auto_buy_price"] = dec["auto_buy_price"]
        if item.get("auto_sell_price") is None:
            item["auto_sell_price"] = dec["auto_sell_price"]
        if item.get("stop_loss_price") is None:
            item["stop_loss_price"] = dec["stop_loss_price"]

    if daily_df is not None and not daily_df.empty:
        last_row = daily_df.iloc[-1]
        if item.get("last_open") is None:
            item["last_open"] = float(last_row["open"])
        if item.get("last_high") is None:
            item["last_high"] = float(last_row["high"])
        if item.get("last_low") is None:
            item["last_low"] = float(last_row["low"])
        if item.get("last_close") is None:
            item["last_close"] = float(last_row["close"])
        if item.get("last_volume") is None:
            item["last_volume"] = float(last_row["volume"])

    if validation is not None:
        item["data_validation"] = validation

    return item


@app.on_event("startup")
def startup():
    init_db()
    start_background_bootstrap()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "coins": list(COINS.keys()),
        "horizons": list(TIMEFRAMES.keys()),
        "required_daily_variables": REQUIRED_DAILY_VARIABLES,
    }


@app.get("/api/coins")
def get_coins():
    return {
        "coins": [
            {"code": "ETH", "symbol": COINS["ETH"], "name": "Ethereum"},
            {"code": "SUI", "symbol": COINS["SUI"], "name": "Sui Network"},
        ],
        "horizons": TIMEFRAMES,
        "required_daily_variables": REQUIRED_DAILY_VARIABLES,
    }


@app.get("/api/prices/latest")
def get_latest_price(coin: str = Query(DEFAULT_COIN, description="ETH atau SUI")):
    return serialize(latest_price(coin.upper()))


@app.get("/api/candles/{coin}")
def get_daily_candles_endpoint(
    coin: str,
    limit: int = Query(60, ge=10, le=365),
):
    """
    Mengembalikan data candlestick harian (open, high, low, close, volume)
    beserta validasi kelengkapan variabel untuk syarat prediksi.
    """
    return serialize(get_coin_candles_and_validation(coin.upper(), limit=limit))


@app.get("/api/predictions/{timeframe}")
def get_latest_prediction(
    timeframe: str,
    coin: str = Query(DEFAULT_COIN, description="ETH atau SUI"),
):
    coin_code = coin.upper()
    horizon_days = TIMEFRAMES.get(timeframe, {}).get("horizon_days", 1)
    candle_bundle = get_coin_candles_and_validation(coin_code, limit=45)
    validation = candle_bundle["validation"]
    if not validation["valid"]:
        return serialize(
            {
                "coin": coin_code,
                "timeframe": timeframe,
                "prediction_blocked": True,
                "reason": validation["reason"],
                "data_validation": validation,
            }
        )

    daily_df = pd.DataFrame(candle_bundle["candles"]) if candle_bundle["candles"] else None
    pred = latest_prediction(timeframe, coin=coin_code)
    return serialize(
        enrich_prediction(pred, horizon_days=horizon_days, daily_df=daily_df, validation=validation)
    )


@app.get("/api/history/{timeframe}")
def get_prediction_history(
    timeframe: str,
    coin: str = Query(DEFAULT_COIN, description="ETH atau SUI"),
    limit: int = Query(30, ge=1, le=200),
    only_evaluated: bool = Query(False),
):
    coin_code = coin.upper()
    horizon_days = TIMEFRAMES.get(timeframe, {}).get("horizon_days", 1)
    rows = prediction_history(
        timeframe,
        coin=coin_code,
        limit=limit,
        only_evaluated=only_evaluated,
    )
    return serialize([enrich_prediction(r, horizon_days=horizon_days) for r in rows])


@app.get("/api/evaluated/{timeframe}")
def get_evaluated_history(
    timeframe: str,
    coin: str = Query(DEFAULT_COIN, description="ETH atau SUI"),
    limit: int = Query(30, ge=1, le=200),
):
    """
    Mengambil data prediksi yang SUDAH memiliki harga aktual (evaluated = TRUE)
    untuk grafik Aktual vs Prediksi dan perhitungan RMSE, MAE, MAPE.
    """
    coin_code = coin.upper()
    horizon_days = TIMEFRAMES.get(timeframe, {}).get("horizon_days", 1)
    rows = prediction_history(
        timeframe,
        coin=coin_code,
        limit=limit,
        only_evaluated=True,
    )
    return serialize([enrich_prediction(r, horizon_days=horizon_days) for r in rows])


@app.get("/api/evaluation")
def get_evaluation_summary(coin: str = Query(DEFAULT_COIN, description="ETH atau SUI")):
    """
    Mengembalikan ringkasan metrik error (RMSE, MAE, MAPE, Directional Accuracy)
    untuk seluruh horizon (1d, 3d, 7d) pada koin terpilih.
    """
    return serialize(evaluation_metrics_summary(coin.upper()))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            coins_payload = {}
            for coin_code in COINS.keys():
                candle_bundle = get_coin_candles_and_validation(coin_code, limit=45)
                validation = candle_bundle["validation"]
                candles_list = candle_bundle["candles"]
                daily_df = pd.DataFrame(candles_list) if candles_list else None

                if validation["valid"]:
                    preds_map = {
                        tf: enrich_prediction(
                            latest_prediction(tf, coin=coin_code),
                            horizon_days=TIMEFRAMES[tf]["horizon_days"],
                            daily_df=daily_df,
                            validation=validation,
                        )
                        for tf in ("1d", "3d", "7d")
                    }
                else:
                    preds_map = {tf: None for tf in ("1d", "3d", "7d")}

                coins_payload[coin_code] = {
                    "price": latest_price(coin_code),
                    "predictions": preds_map,
                    "evaluation": evaluation_metrics_summary(coin_code),
                    "candles": candles_list,
                    "validation": validation,
                }

            default_data = coins_payload.get(DEFAULT_COIN, {})
            payload = {
                "coins": coins_payload,
                "price": default_data.get("price"),
                "predictions": default_data.get("predictions"),
            }
            await websocket.send_text(json.dumps(serialize(payload)))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        return
