import sys
import os
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
from datetime import datetime, timedelta
import ccxt

# --- TRIK IMPORT CONFIG ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import db, SYMBOL, TIMEFRAMES

# Lokasi penyimpanan model (file otak AI)
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'xgb_15m.pkl')

def fetch_market_data():
    """Mengambil 500 candle terakhir timeframe 15m dari Indodax"""
    try:
        exchange = ccxt.indodax()
        # Ambil limit 500 agar cukup untuk training kilat
        ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe='15m', limit=500)
        
        # Konversi ke Pandas DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"❌ Error fetching OHLCV: {e}")
        return None

def add_indicators(df):
    """Feature Engineering: Membuat indikator teknikal manual"""
    df = df.copy()
    
    # 1. RSI (Relative Strength Index) - Periode 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 2. EMA (Exponential Moving Average)
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # 3. MACD (Moving Average Convergence Divergence)
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # 4. Volatilitas (Rolling Std Dev)
    df['Volatility'] = df['close'].rolling(window=20).std()
    
    # Hapus baris NaN (kosong) akibat perhitungan indikator
    df.dropna(inplace=True)
    return df

def train_and_predict():
    print("🤖 Starting XGBoost Engine (15m)...")
    
    # 1. Ambil Data
    df = fetch_market_data()
    if df is None: return
    
    # 2. Tambah Indikator
    df = add_indicators(df)
    
    # 3. Siapkan Fitur (X) dan Target (y)
    # Fitur = Indikator teknikal
    features = ['close', 'volume', 'RSI', 'EMA_9', 'EMA_21', 'MACD', 'Volatility']
    
    X = df[features]
    # Target = Harga Close GESER 1 baris ke atas (Harga masa depan)
    y = df['close'].shift(-1)
    
    # Hapus baris terakhir karena tidak punya target masa depan (y=NaN)
    # Tapi simpan baris terakhir ini untuk diprediksi nanti (X_latest)
    X_train = X.iloc[:-1]
    y_train = y.iloc[:-1]
    X_latest = X.iloc[[-1]] # Data candle terakhir yang baru saja close
    
    # 4. Training Model (Re-train setiap jalan agar selalu update pola terbaru)
    # XGBoost Regressor
    model = xgb.XGBRegressor(
        n_estimators=100, 
        learning_rate=0.05, 
        max_depth=5, 
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # (Opsional) Simpan model jika ingin dipamerkan
    joblib.dump(model, MODEL_PATH)
    
    # 5. Lakukan Prediksi untuk 15 menit ke depan
    prediction = model.predict(X_latest)[0]
    current_price = X_latest['close'].values[0]
    
    # Hitung perubahan (Naik/Turun)
    change_pct = ((prediction - current_price) / current_price) * 100
    signal = "BULLISH" if prediction > current_price else "BEARISH"
    
    print(f"💵 Current (15m close): Rp {current_price:,.0f}")
    print(f"🔮 Prediction (Next 15m): Rp {prediction:,.0f}")
    print(f"📊 Signal: {signal} ({change_pct:.2f}%)")
    
    # 6. Simpan ke Firestore
    save_prediction(prediction, current_price, signal, change_pct)

def save_prediction(pred_price, curr_price, signal, change):
    try:
        data = {
            'timeframe': '15m',
            'predicted_price': float(pred_price),
            'current_price_at_prediction': float(curr_price),
            'signal': signal,
            'change_percent': float(change),
            'created_at': datetime.now(),
            'model': 'XGBoost Regressor'
        }
        
        # Simpan ke predictions/latest_15m (untuk UI cepat)
        db.collection('predictions').document('latest_15m').set(data)
        
        # Simpan history evaluasi (untuk hitung akurasi nanti)
        # Gunakan ID timestamp agar unik
        doc_id = datetime.now().isoformat()
        db.collection('history_15m').document(doc_id).set(data)
        
        print("💾 Prediction saved to Firestore!")
        
    except Exception as e:
        print(f"❌ Error saving prediction: {e}")

# --- TEST RUN ---
if __name__ == "__main__":
    train_and_predict()