import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Mencegah inisialisasi ganda
if not firebase_admin._apps:
    # Pastikan path ke serviceAccountKey.json benar
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

# Export client database agar bisa dipakai di file lain
db = firestore.client()

# Konfigurasi Global
SYMBOL = 'ETH/IDR'
TIMEFRAMES = {
    '15m': '15m',  # XGBoost
    '1h': '1h',    # LSTM
    '1w': '1d',    # Prophet (pakai data harian untuk forecast mingguan)
    '1mo': '1d'    # Prophet
}

print("✅ System Configuration Loaded & Database Connected")