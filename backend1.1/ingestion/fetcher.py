import os
import sys
from datetime import datetime
import ccxt
import pandas as pd
import pytz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import COINS, DEFAULT_COIN, REQUIRED_DAILY_VARIABLES
from database import get_daily_candles, insert_price, upsert_daily_candles
from decision.signal_engine import validate_daily_ohlcv

WIB_TZ = pytz.timezone("Asia/Jakarta")

try:
    exchange = ccxt.indodax({"enableRateLimit": True})
    print(f"✅ Exchange Initialized: {exchange.id}")
except Exception as e:
    exchange = None
    print(f"❌ Failed to initialize exchange: {e}")


def get_indodax_price(coin: str = DEFAULT_COIN):
    """
    Mengambil data ticker real-time dari Indodax beserta open, high, low, close (price), volume.
    """
    coin_code = coin.upper()
    symbol = COINS.get(coin_code, f"{coin_code}/IDR")
    try:
        ex = exchange or ccxt.indodax({"enableRateLimit": True})
        ticker = ex.fetch_ticker(symbol)

        last_price = float(ticker["last"])
        open_price = float(ticker.get("open") or last_price)
        high_price = float(ticker.get("high") or last_price)
        low_price = float(ticker.get("low") or last_price)
        quote_vol = ticker.get("quoteVolume")
        base_vol = ticker.get("baseVolume") or 0.0
        if quote_vol is None:
            quote_vol = float(base_vol) * last_price

        data = {
            "coin": coin_code,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "price": last_price,
            "close": last_price,
            "volume": float(quote_vol or 0.0),
            "timestamp": datetime.now(pytz.utc),
        }
        return data

    except ccxt.NetworkError as e:
        print(f"⚠️ [{coin_code}] Network Error (Retrying...): {e}")
    except ccxt.ExchangeError as e:
        print(f"⚠️ [{coin_code}] Exchange Error: {e}")
    except Exception as e:
        print(f"❌ [{coin_code}] Unknown Error: {e}")

    return None


def fetch_ohlcv_df(
    coin: str = DEFAULT_COIN,
    timeframe: str = "1d",
    limit: int = 500,
    only_closed: bool = False,
):
    """
    Mengambil data candle OHLCV riil (open, high, low, close, volume) dari Indodax.
    Untuk timeframe='1d', setiap baris merepresentasikan 1 hari kalender WIB (Asia/Jakarta).
    Jika only_closed=True, maka candle hari berjalan (yang belum tutup pukul 23:59 WIB)
    tidak disertakan karena nilai Close hariannya belum lengkap/final.
    """
    coin_code = coin.upper()
    symbol = COINS.get(coin_code, f"{coin_code}/IDR")
    today_wib = datetime.now(WIB_TZ).date()

    try:
        ex = exchange or ccxt.indodax({"enableRateLimit": True})
        if timeframe != "1d":
            raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if not raw:
                return None
            df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            return df

        # Untuk daily (1d), gabungkan histori 1d Indodax + agregasi 1h per hari kalender WIB
        frames = []
        raw_1d = ex.fetch_ohlcv(symbol, timeframe="1d", limit=limit)
        if raw_1d:
            df_1d = pd.DataFrame(
                raw_1d, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df_1d["timestamp"] = pd.to_datetime(df_1d["timestamp"], unit="ms", utc=True)
            df_1d["wib_date"] = df_1d["timestamp"].dt.tz_convert(WIB_TZ).dt.date
            frames.append(df_1d)

        raw_1h = ex.fetch_ohlcv(symbol, timeframe="1h", limit=1500)
        if raw_1h:
            df_1h = pd.DataFrame(
                raw_1h, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df_1h["timestamp"] = pd.to_datetime(df_1h["timestamp"], unit="ms", utc=True)
            df_1h["wib_dt"] = df_1h["timestamp"].dt.tz_convert(WIB_TZ)
            df_1h["wib_date"] = df_1h["wib_dt"].dt.date
            daily_from_1h = (
                df_1h.sort_values("timestamp")
                .groupby("wib_date", as_index=False)
                .agg(
                    open=("open", "first"),
                    high=("high", "max"),
                    low=("low", "min"),
                    close=("close", "last"),
                    volume=("volume", "sum"),
                )
            )
            frames.append(daily_from_1h)

        if not frames:
            return None

        combined = pd.concat(frames, ignore_index=True)
        # Prioritaskan hasil agregasi 1h untuk tanggal-tanggal terbaru karena paling presisi per hari WIB
        combined = combined.drop_duplicates(subset=["wib_date"], keep="last").sort_values("wib_date")

        # Representasikan timestamp setiap candle harian sebagai pukul 00:00 WIB pada tanggal tersebut
        combined["timestamp"] = combined["wib_date"].apply(
            lambda d: WIB_TZ.localize(datetime(d.year, d.month, d.day, 0, 0, 0)).astimezone(pytz.utc)
        )
        combined["is_closed"] = combined["wib_date"] < today_wib

        df = combined[["timestamp", "open", "high", "low", "close", "volume", "wib_date", "is_closed"]].reset_index(
            drop=True
        )

        # Simpan ke tabel daily_candles (baik yang sudah closed maupun yang sedang berjalan untuk info live)
        if not df.empty:
            candles_to_save = df.tail(120).to_dict(orient="records")
            upsert_daily_candles(candles_to_save, coin=coin_code)

        if only_closed:
            df = df[df["is_closed"]].reset_index(drop=True)

        return df
    except Exception as e:
        print(f"❌ [{coin_code}] Error fetching OHLCV ({timeframe}): {e}")
        if timeframe == "1d":
            cached = get_daily_candles(coin_code, limit=limit)
            if cached:
                df_cache = pd.DataFrame(cached)
                df_cache["timestamp"] = pd.to_datetime(df_cache["timestamp"], utc=True)
                df_cache["wib_date"] = df_cache["timestamp"].dt.tz_convert(WIB_TZ).dt.date
                df_cache["is_closed"] = df_cache["wib_date"] < today_wib
                if only_closed:
                    df_cache = df_cache[df_cache["is_closed"]].reset_index(drop=True)
                return df_cache
        return None


def fetch_daily_ohlcv_validated(
    coin: str = DEFAULT_COIN,
    limit: int = 500,
    min_rows: int = 20,
    only_closed: bool = True,
):
    """
    Mengambil data harian (daily) yang SUDAH LENGKAP / CLOSED (secara default only_closed=True)
    dan memvalidasi kelengkapan 5 variabel wajib: open, high, low, close, volume.
    Candle tanggal hari ini yang sedang berjalan (belum memiliki Close akhir hari)
    tidak dijadikan data aktual maupun input final agar prediksi Close hari ini murni real.
    """
    df = fetch_ohlcv_df(coin, timeframe="1d", limit=limit, only_closed=only_closed)
    validation = validate_daily_ohlcv(df, min_rows=min_rows)
    if not validation["valid"]:
        print(f"⛔ [{coin.upper()}] Validasi Data Harian Gagal: {validation['message']}")
        return None, validation
    clean_df = df.dropna(subset=REQUIRED_DAILY_VARIABLES).reset_index(drop=True)
    return clean_df, validation


def save_to_database(data: dict, coin: str | None = None):
    """
    Menyimpan data harga live ke tabel prices di PostgreSQL.
    """
    try:
        target_coin = (coin or data.get("coin") or DEFAULT_COIN).upper()
        insert_price(data, coin=target_coin)
        print(
            f"💾 [{target_coin}] Saved Live Price: Rp {data['price']:,.0f} "
            f"(O:{data.get('open', 0):,.0f} H:{data.get('high', 0):,.0f} L:{data.get('low', 0):,.0f}) "
            f"at {data['timestamp'].isoformat()}"
        )
        return True
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return False


def ingest_all_coins():
    """
    Mengambil dan menyimpan harga terbaru serta memperbarui candle daily (OHLCV)
    untuk seluruh koin di COINS (ETH & SUI).
    """
    results = {}
    for coin_code in COINS.keys():
        price_data = get_indodax_price(coin_code)
        if price_data:
            save_to_database(price_data, coin=coin_code)
            results[coin_code] = price_data
        fetch_ohlcv_df(coin_code, timeframe="1d", limit=90, only_closed=False)
    return results


if __name__ == "__main__":
    print("🔬 Testing Multi-Coin Daily OHLCV Ingestion Engine (ETH & SUI)...")
    ingest_all_coins()
