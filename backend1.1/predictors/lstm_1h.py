import sys
import os
import numpy as np
import pandas as pd
import ccxt
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from datetime import datetime

# --- TRIK IMPORT CONFIG ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import db, SYMBOL

# --- KONFIGURASI MODEL ---
LOOKBACK = 24  # Kita melihat 24 jam ke belakang untuk memprediksi jam berikutnya
EPOCHS = 20    # Jumlah putaran belajar (Jaga agar tetap kecil biar cepat di scheduler)
BATCH_SIZE = 32

def fetch_hourly_data():
    """Ambil data 1 jam (1h) sebanyak 1500 candle terakhir (~2 bulan)"""
    try:
        exchange = ccxt.indodax()
        ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe='1h', limit=1500)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"❌ Error fetching hourly data: {e}")
        return None

def create_dataset(dataset, look_back=1):
    """Fungsi pembentuk Sliding Window untuk LSTM"""
    dataX, dataY = [], []
    for i in range(len(dataset) - look_back - 1):
        a = dataset[i:(i + look_back), 0]
        dataX.append(a)
        dataY.append(dataset[i + look_back, 0])
    return np.array(dataX), np.array(dataY)

def train_and_predict():
    print("🧠 Starting LSTM Engine (1h)...")
    
    # 1. Ambil Data
    df = fetch_hourly_data()
    if df is None: return

    # Ambil kolom 'close' saja untuk prediksi sederhana Univariate
    data = df['close'].values.reshape(-1, 1)
    
    # 2. Normalisasi (PENTING SEKALI!)
    # Mengubah Rp 50.000.000 menjadi angka antara 0 dan 1
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data)

    # 3. Siapkan Data Training
    # Gunakan sliding window (lookback)
    X, y = create_dataset(scaled_data, LOOKBACK)
    
    # Reshape input menjadi [samples, time steps, features] (Wajib buat LSTM)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))

    # 4. Bangun Arsitektur LSTM
    model = Sequential()
    # Layer 1: LSTM
    model.add(LSTM(units=50, return_sequences=True, input_shape=(LOOKBACK, 1)))
    model.add(Dropout(0.2)) # Buang 20% neuron biar gak "menghafal" (Overfitting)
    
    # Layer 2: LSTM
    model.add(LSTM(units=50))
    model.add(Dropout(0.2))
    
    # Layer Output
    model.add(Dense(units=1)) # Output cuma 1 angka (Harga)

    model.compile(optimizer='adam', loss='mean_squared_error')

    # 5. Training
    # verbose=0 agar terminal tidak penuh spam progress bar
    model.fit(X, y, epochs=EPOCHS, batch_size=BATCH_SIZE, verbose=0)
    
    # 6. Prediksi Masa Depan
    # Ambil data candle terakhir sesuai jumlah lookback
    last_window = scaled_data[-LOOKBACK:]
    last_window = last_window.reshape(1, LOOKBACK, 1)
    
    predicted_scaled = model.predict(last_window, verbose=0)
    
    # 7. Denormalisasi (Kembalikan ke Rupiah)
    predicted_price = scaler.inverse_transform(predicted_scaled)[0][0]
    current_price = df['close'].iloc[-1]

    # Hitung Perubahan
    change_pct = ((predicted_price - current_price) / current_price) * 100
    signal = "BULLISH" if predicted_price > current_price else "BEARISH"

    print(f"💵 Current (1h close): Rp {current_price:,.0f}")
    print(f"🔮 Prediction (Next 1h): Rp {predicted_price:,.0f}")
    print(f"📊 Signal: {signal} ({change_pct:.2f}%)")

    # 8. Simpan ke Firestore
    save_prediction(predicted_price, current_price, signal, change_pct)

def save_prediction(pred_price, curr_price, signal, change):
    try:
        data = {
            'timeframe': '1h',
            'predicted_price': float(pred_price),
            'current_price_at_prediction': float(curr_price),
            'signal': signal,
            'change_percent': float(change),
            'created_at': datetime.now(),
            'model': 'LSTM (TensorFlow)'
        }
        
        # Simpan latest untuk UI
        db.collection('predictions').document('latest_1h').set(data)
        
        # Simpan history untuk evaluasi
        doc_id = datetime.now().isoformat()
        db.collection('history_1h').document(doc_id).set(data)
        
        print("💾 LSTM Prediction saved to Firestore!")
        
    except Exception as e:
        print(f"❌ Error saving prediction: {e}")

if __name__ == "__main__":
    train_and_predict()