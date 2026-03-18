import sys
import os
import pandas as pd
import ccxt
from prophet import Prophet
from datetime import datetime

# --- TRIK IMPORT CONFIG ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import db, SYMBOL

def fetch_daily_data():
    """Ambil data harian (1d) sebanyak 730 hari (2 tahun)"""
    try:
        exchange = ccxt.indodax()
        # Prophet butuh data panjang untuk lihat seasonality
        ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe='1d', limit=730)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"❌ Error fetching daily data: {e}")
        return None

def train_and_forecast():
    print("🔮 Starting Prophet Engine (Weekly Forecast)...")
    
    # 1. Ambil Data
    df = fetch_daily_data()
    if df is None: return

    # 2. Format Data Khusus Prophet
    # Prophet WAJIB kolomnya bernama 'ds' (tanggal) dan 'y' (nilai)
    prophet_df = df[['timestamp', 'close']].rename(columns={'timestamp': 'ds', 'close': 'y'})

    # 3. Setup Model
    # daily_seasonality=True karena kripto buka 24 jam setiap hari
    model = Prophet(daily_seasonality=True, yearly_seasonality=True)
    
    # 4. Training
    model.fit(prophet_df)

    # 5. Buat Masa Depan (7 Hari ke depan)
    future = model.make_future_dataframe(periods=7) # Tambah 7 hari kosong ke depan
    
    # 6. Prediksi
    forecast = model.predict(future)
    
    # Ambil data hari ke-7 dari sekarang (Data terakhir di dataframe)
    next_week = forecast.iloc[-1]
    
    predicted_price = next_week['yhat']        # Harga Tengah
    lower_bound = next_week['yhat_lower']      # Batas Bawah (Pesimis)
    upper_bound = next_week['yhat_upper']      # Batas Atas (Optimis)
    
    current_price = df['close'].iloc[-1]
    
    # Hitung Tren
    signal = "BULLISH TREND" if predicted_price > current_price else "BEARISH TREND"
    change_pct = ((predicted_price - current_price) / current_price) * 100

    print(f"💵 Current Price: Rp {current_price:,.0f}")
    print(f"📅 Forecast (7 Days later):")
    print(f"   ► Target: Rp {predicted_price:,.0f}")
    print(f"   ► Range: Rp {lower_bound:,.0f} - Rp {upper_bound:,.0f}")
    print(f"📊 Signal: {signal} ({change_pct:.2f}%)")

    # 7. Simpan ke Firestore
    save_forecast(predicted_price, lower_bound, upper_bound, current_price, signal)

def save_forecast(pred, lower, upper, curr, signal):
    try:
        data = {
            'timeframe': '1w', # 1 Week
            'predicted_price': float(pred),
            'lower_bound': float(lower),
            'upper_bound': float(upper),
            'current_price_at_prediction': float(curr),
            'signal': signal,
            'created_at': datetime.now(),
            'model': 'Facebook Prophet'
        }
        
        # Simpan latest
        db.collection('predictions').document('latest_1w').set(data)
        
        # Simpan history
        doc_id = datetime.now().isoformat()
        db.collection('history_1w').document(doc_id).set(data)
        
        print("💾 Forecast saved to Firestore!")
        
    except Exception as e:
        print(f"❌ Error saving forecast: {e}")

if __name__ == "__main__":
    train_and_forecast()