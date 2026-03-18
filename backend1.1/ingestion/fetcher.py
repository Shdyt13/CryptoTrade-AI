import ccxt
import time
import sys
import os
from datetime import datetime
import pytz

# --- TRIK IMPORT CONFIG ---
# Menambahkan folder induk (backend1.1) ke jalur pencarian Python
# agar bisa import 'config.py' meskipun file ini ada di dalam folder 'ingestion'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import db, SYMBOL  # Import database & simbol ETH/IDR

# --- SETUP INDODAX ---
try:
    exchange = ccxt.indodax()
    print(f"✅ Exchange Initialized: {exchange.id}")
except Exception as e:
    print(f"❌ Failed to initialize exchange: {e}")

def get_indodax_price():
    """
    Mengambil data ticker terbaru dari Indodax.
    Mengembalikan Dictionary data jika sukses, atau None jika gagal.
    """
    try:
        # Fetch ticker (harga saat ini, high, low, vol)
        ticker = exchange.fetch_ticker(SYMBOL)
        
        # Kita ambil data penting saja
        data = {
            'price': float(ticker['last']),      # Harga terakhir
            'high': float(ticker['high']),       # Tertinggi 24h
            'low': float(ticker['low']),         # Terendah 24h
            'volume': float(ticker['quoteVolume']), # Volume dalam IDR
            'timestamp': datetime.now(pytz.utc)  # Waktu UTC (Standar Server)
        }
        return data

    except ccxt.NetworkError as e:
        print(f"⚠️ Network Error (Retrying...): {e}")
    except ccxt.ExchangeError as e:
        print(f"⚠️ Exchange Error (Indodax Maintenance?): {e}")
    except Exception as e:
        print(f"❌ Unknown Error: {e}")
    
    return None

def save_to_firestore(data):
    """
    Menyimpan data harga ke koleksi 'prices' di Firestore.
    """
    try:
        # 1. Simpan history untuk grafik (Document ID = Timestamp agar urut)
        # Gunakan format ISO string untuk ID dokumen agar mudah di-sort
        doc_id = data['timestamp'].isoformat()
        
        # Simpan ke collection 'prices' (Data Historis)
        db.collection('prices').document(doc_id).set(data)

        # 2. Simpan 'latest_price' untuk tampilan cepat di Kartu Utama
        # Ini agar frontend tidak perlu query data historis berat cuma buat lihat harga sekarang
        latest_data = data.copy()
        latest_data['updated_at'] = firestore_server_time() # Helper function
        
        db.collection('prices').document('latest').set(latest_data)
        
        print(f"💾 Saved: Rp {data['price']:,.0f} at {doc_id}")
        return True

    except Exception as e:
        print(f"❌ Database Error: {e}")
        return False

# Helper untuk timestamp server firebase
def firestore_server_time():
    from firebase_admin import firestore
    return firestore.SERVER_TIMESTAMP

# --- TEST RUN (Jika file ini dijalankan langsung) ---
if __name__ == "__main__":
    print("🔬 Testing Ingestion Engine...")
    
    # Coba ambil data sekali
    price_data = get_indodax_price()
    
    if price_data:
        print(f"📈 Data Received: {price_data}")
        # Coba simpan
        save_to_firestore(price_data)
        print("✅ Test Success! Cek Firebase Console Anda.")
    else:
        print("❌ Test Failed: No Data.")