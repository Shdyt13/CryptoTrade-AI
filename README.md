# Multi-Coin Crypto Intelligent Prediction System (ETH & SUI) 🚀

![Status](https://img.shields.io/badge/Status-Active-success)
![Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%20%7C%20PostgreSQL-blue)
![Coins](https://img.shields.io/badge/Assets-ETH%2FIDR%20%26%20SUI%2FIDR-indigo)

> **Sistem Prediksi Harga Kripto Multi-Aset (Ethereum `ETH/IDR` & Sui `SUI/IDR`) berbasis AI dengan 3 Horizon Prediksi (1, 3, dan 7 Hari), Rekomendasi Keputusan Buy/Hold/Sell, dan Evaluasi Error (RMSE, MAE, MAPE).**

---

## 🌟 Fitur Utama

### 1. 🪙 Dukungan Multi-Aset Kripto (ETH & SUI)
Mendukung pemantauan harga pasar langsung (*live ticker* dari **Indodax API**) serta pemodelan prediksi independen untuk:
- **Ethereum (`ETH/IDR`)**
- **Sui Network (`SUI/IDR`)**

### 2. 🧠 3 Horizon Prediksi & Algoritma Khusus
- **Prediksi 1 Hari Kedepan (`1d`) — Model LSTM:**
  Menggunakan jaringan saraf sekuensial *Long Short-Term Memory* (TensorFlow/Keras) untuk memodelkan pola harga 1 hari ke depan.
- **Prediksi 3 Hari Kedepan (`3d`) — Model Hybrid LSTM + XGBoost (Residual Correction Stacking):**
  Menggunakan pendekatan *Residual Correction Stacking* di mana **LSTM** bertindak sebagai *base-learner* untuk menangkap tren urutan waktu, lalu **XGBoost Regressor** bertindak sebagai *meta-learner* yang mempelajari dan mengoreksi *residual error* ($r = y_{\text{aktual}} - \hat{y}_{\text{LSTM}}$) menggunakan indikator teknikal (RSI, EMA, MACD, Bollinger Width, Volatility).
- **Prediksi 7 Hari Kedepan (`7d`) — Model Facebook Prophet:**
  Memprediksi tren jangka menengah-panjang 7 hari ke depan beserta rentang batas bawah (*lower bound*) dan batas atas (*upper bound*).

### 3. ⚖️ Sistem Keputusan Trading (Buy / Hold / Sell) dengan Rentang Persentase
Setiap horizon prediksi dilengkapi mesin keputusan (*Signal Decision Engine*) yang menghitung distribusi probabilitas/keyakinan keputusan yang berjumlah 100%, contohnya:
- **SELL:** `70%` | **HOLD:** `20%` | **BUY:** `10%`

### 4. 📈 Grafik Aktual vs Prediksi
Setiap data prediksi yang telah memiliki harga aktual dimasukkan secara otomatis ke dalam **Grafik Aktual vs Prediksi** untuk memvisualisasikan seberapa akurat prediksi mengikuti pola pergerakan harga sebenarnya.

### 5. 📊 Grafik Evaluasi Tingkat Error (RMSE, MAE, dan MAPE)
Menyediakan metrik dan grafik evaluasi komprehensif:
- **RMSE (*Root Mean Squared Error*)** dalam Rupiah
- **MAE (*Mean Absolute Error*)** dalam Rupiah
- **MAPE (*Mean Absolute Percentage Error*)** dalam Persen (`%`)

---

## 📂 Struktur Proyek

```bash
ethereum-trend-predictor/
├── backend1.1/
│   ├── api.py                      # FastAPI REST API & WebSocket (Multi-Coin ETH & SUI)
│   ├── config.py                   # Konfigurasi koin (ETH, SUI) & horizon (1d, 3d, 7d)
│   ├── database.py                 # Skema PostgreSQL & query evaluasi (RMSE, MAE, MAPE)
│   ├── decision/
│   │   └── signal_engine.py        # Kalkulasi keputusan Buy / Hold / Sell (%)
│   ├── ingestion/
│   │   └── fetcher.py              # Pengambilan data Indodax untuk ETH/IDR & SUI/IDR
│   ├── predictors/
│   │   ├── lstm_1d.py              # Prediksi 1 Hari menggunakan LSTM
│   │   └── hybrid_3d.py            # Prediksi 3 Hari menggunakan Hybrid LSTM + XGBoost
│   ├── long_term/
│   │   └── prophet_forecast.py     # Prediksi 7 Hari menggunakan Facebook Prophet
│   ├── evaluation/
│   │   ├── evaluator.py            # Evaluasi otomatis prediksi terhadap harga aktual
│   │   └── metrics.py              # Perhitungan RMSE, MAE, MAPE, Directional Accuracy
│   └── scheduler/
│       └── main_runner.py          # Worker penjadwalan otomatis
│
├── frontend_v1.1/
│   └── src/
│       ├── App.jsx                 # Dashboard utama + pemilih aset (ETH & SUI)
│       ├── components/
│       │   ├── PriceTicker.jsx     # Live ticker ETH/IDR & SUI/IDR
│       │   ├── PredictionCard.jsx  # Card prediksi 1d, 3d, 7d + bar keputusan Buy/Hold/Sell
│       │   └── Analytics.jsx       # Grafik Aktual vs Prediksi & Grafik RMSE, MAE, MAPE
│       └── hooks/
│           └── useRealtimeData.js  # Koneksi WebSocket & REST API
│
└── docker-compose.yml              # Orkestrasi PostgreSQL, API, Worker, dan Frontend
```

---

## 🚀 Cara Menjalankan Sistem

### Menggunakan Docker Compose
```powershell
docker compose up -d --build
```
- **Dashboard UI:** `http://localhost` (atau `http://127.0.0.1`)
- **Backend API:** `http://localhost:8000`
- **Health Check:** `http://localhost:8000/health`

### Menjalankan Secara Lokal (Tanpa Docker)
1. Pastikan PostgreSQL aktif dan set `DATABASE_URL`:
   ```powershell
   $env:DATABASE_URL = "postgresql://eth_predictor:eth_predictor@localhost:5432/eth_predictor"
   ```
2. Jalankan Backend API & Worker:
   ```powershell
   cd backend1.1
   pip install -r requirements.txt
   python -m uvicorn api:app --reload
   python scheduler\main_runner.py
   ```
3. Jalankan Frontend:
   ```powershell
   cd frontend_v1.1
   npm install
   npm run dev
   ```
