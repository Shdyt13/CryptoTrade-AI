# CryptoTrade AI — Multi-Coin Daily OHLCV Trend & Strategy Predictor (ETH & SUI) 📈

![Status](https://img.shields.io/badge/Status-Active-success)
![Stack](https://img.shields.io/badge/Stack-FastAPI%20%7C%20React%20%7C%20PostgreSQL%20%7C%20TensorFlow%20%7C%20XGBoost-blue)
![Coins](https://img.shields.io/badge/Assets-ETH%2FIDR%20%26%20SUI%2FIDR-indigo)
![Models](https://img.shields.io/badge/Models-LSTM%20%7C%20Hybrid%20LSTM%2BXGB%20%7C%20Hybrid%20TCN%2BXGB-emerald)

> **Sistem Prediksi Harga `Close` Harian & Strategi Trading Kripto Multi-Aset (Ethereum `ETH/IDR` & Sui Network `SUI/IDR`) berbasis AI dengan Input Wajib Daily OHLCV (`Open, High, Low, Close, Volume`), 3 Horizon Prediksi (1, 3, dan 7 Hari), Rekomendasi Keputusan `Buy / Hold / Sell`, Strategi `Auto Buy & Auto Sell`, Grafik Candlestick, serta Evaluasi Aktual vs Prediksi.**

🔗 **Repository:** [https://github.com/Shdyt13/CryptoTrade-AI](https://github.com/Shdyt13/CryptoTrade-AI)

---

## 🌟 Fitur Utama

### 1. 🪙 Dukungan Multi-Aset Kripto dengan Ikon Resmi (`ETH/IDR` & `SUI/IDR`)
Memantau harga pasar *spot* secara langsung (*real-time ticker* & *daily OHLCV* dari **Indodax API**) serta menjalankan pemodelan prediksi independen untuk:
- **Ethereum (`ETH/IDR`)**
- **Sui Network (`SUI/IDR`)**

### 2. 🛡️ Validasi Ketat 5 Variabel Input Harian (*Daily OHLCV Guard*)
- Seluruh proses pelatihan dan prediksi menggunakan data harian (*daily candles*) yang **sudah tutup (*closed*)** dengan **5 variabel wajib**:
  1. `open` (Harga Pembukaan Harian)
  2. `high` (Harga Tertinggi Harian)
  3. `low` (Harga Terendah Harian)
  4. `close` (Harga Penutupan Harian)
  5. `volume` (Volume Transaksi Harian)
- **Aturan Validasi:** Apabila data harian belum memiliki kelima variabel tersebut secara lengkap dan valid, maka **prediksi tidak dapat dilakukan** (sistem otomatis menangguhkan prediksi dan menampilkan status validasi variabel).

### 3. 🧠 3 Horizon Prediksi Harga `Close` & Algoritma Deep Learning / Hybrid Stacking
| Horizon | Algoritma / Model | Deskripsi Arsitektur |
| :--- | :--- | :--- |
| **1 Hari (`1d`)** | **Multivariate LSTM** | Jaringan saraf sekuensial *Long Short-Term Memory* (TensorFlow/Keras) dengan input matriks 5 variabel harian (`Open, High, Low, Close, Volume`) untuk memprediksi harga `Close` 1 hari ke depan. |
| **3 Hari (`3d`)** | **Hybrid LSTM + XGBoost** *(Residual Correction Stacking)* | **LSTM** bertindak sebagai *base-learner* penangkap pola sekuensial harian, lalu **XGBoost Regressor** bertindak sebagai *meta-learner* yang mengoreksi *residual error* ($\hat{y}_{\text{hybrid}} = \hat{y}_{\text{LSTM}} + \hat{r}_{\text{XGB}}$) menggunakan indikator teknikal harian (`RSI`, `EMA_7`, `EMA_21`, `MACD`, `Volatility`, `Daily_Range`). |
| **7 Hari (`7d`)** | **Hybrid TCN + XGBoost** *(Residual Correction Stacking)* | **Temporal Convolutional Network (TCN)** dengan *Causal Dilated 1D Convolutions* (`dilation_rate = 1, 2, 4`) & *Residual Skip Connections* sebagai *base-learner*, dikombinasikan dengan **XGBoost Regressor** sebagai *meta-learner* pengoreksi residual ($\hat{y}_{\text{hybrid}} = \hat{y}_{\text{TCN}} + \hat{r}_{\text{XGB}}$) untuk memprediksi harga `Close` 7 hari ke depan. |

### 4. 🎯 Saran Keputusan (`Buy / Hold / Sell`) & Target `Auto Buy` / `Auto Sell`
Setiap horizon prediksi menampilkan:
- **Prediksi Harga `Close`** pada tanggal target.
- **Saran Kebutuhan Trading (`BUY`, `HOLD`, atau `SELL`)** beserta distribusi persentase keyakinan yang berjumlah 100% (contoh: `Buy 78% | Hold 16% | Sell 6%`).
- **Target `Auto Buy` (*Limit Entry*)** & **Target `Auto Sell` (*Take Profit*)** yang dihitung dari proyeksi harga `Close` dan rata-rata rentang volatilitas harian (*Daily ATR/Range*) untuk mempermudah persiapan order otomatis.

### 5. 🕯️ Grafik Candlestick Harian Interaktif
Menampilkan grafik **Candlestick Harian (`Open, High, Low, Close, Volume`)** yang dilengkapi garis acuan:
- **Prediksi Harga `Close`** (`1d`, `3d`, atau `7d`)
- **Target `Auto Sell` (*Take Profit*)**
- **Target `Auto Buy` (*Limit Entry*)**

### 6. 📊 Grafik Aktual vs Prediksi & Tabel Selisih Kesalahan Prediksi
- Hanya mengevaluasi tanggal-tanggal yang candle hariannya **sudah selesai/tutup (*closed*)** sehingga nilai `Close` aktual benar-benar *real* dan final.
- Menampilkan **Grafik Harga `Close` Aktual vs Prediksi** untuk melihat seberapa dekat model mengikuti pola pergerakan harga sebenarnya.
- Menyediakan **Tabel Selisih Kesalahan Prediksi Berdasarkan Data Aktual** yang merinci:
  - Tanggal Target (`WIB`)
  - Harga Prediksi `Close` (`Rp`)
  - Harga Aktual `Close` (`Rp`)
  - Besar Selisih Kesalahan dalam Rupiah (`Rp |Prediksi - Aktual|`) dan Persentase (`%`)

---

## 📂 Struktur Proyek

```bash
CryptoTrade-AI/
├── backend1.1/
│   ├── api.py                      # FastAPI REST API & WebSocket (ETH & SUI, Daily Candles & Predictions)
│   ├── bootstrap.py                # Inisialisasi awal data riil Indodax & pelatihan model asli
│   ├── config.py                   # Konfigurasi koin (ETH, SUI), variabel wajib OHLCV, & horizon (1d, 3d, 7d)
│   ├── database.py                 # Skema PostgreSQL (prices, daily_candles, predictions, accuracy)
│   ├── decision/
│   │   └── signal_engine.py        # Validasi Daily OHLCV, skor Buy/Hold/Sell (%), & kalkulasi Auto Buy/Sell
│   ├── ingestion/
│   │   └── fetcher.py              # Pengambilan & sinkronisasi data harian (Daily OHLCV) Indodax
│   ├── predictors/
│   │   ├── lstm_1d.py              # Horizon 1 Hari: Multivariate LSTM (Daily OHLCV)
│   │   ├── hybrid_3d.py            # Horizon 3 Hari: Hybrid LSTM + XGBoost (Residual Stacking)
│   │   └── hybrid_tcn_7d.py        # Horizon 7 Hari: Hybrid TCN + XGBoost (Residual Stacking)
│   ├── evaluation/
│   │   ├── evaluator.py            # Evaluasi otomatis prediksi terhadap harga Close aktual yang sudah tutup
│   │   └── metrics.py              # Fungsi perhitungan selisih & akurasi arah
│   └── scheduler/
│       └── main_runner.py          # Worker penjadwalan otomatis (Ingestion, Prediction, Evaluation)
│
├── frontend_v1.1/
│   ├── index.html                  # Entry HTML dengan favicon & tema CryptoTrade AI
│   ├── public/
│   │   └── trading-icon.svg        # Ikon vektor bertema trading candlestick
│   └── src/
│       ├── App.jsx                 # Layout Dashboard Utama terpadu (ETH/IDR & SUI/IDR)
│       ├── components/
│       │   ├── CoinIcons.jsx       # Ikon SVG resmi Ethereum (ETH), Sui (SUI), & Trading Logo
│       │   ├── Sidebar.jsx         # Navigasi sidebar & pemilih aset koin
│       │   ├── PriceTicker.jsx     # Panel harga spot real-time Indodax (24h High/Low & Volume)
│       │   ├── PredictionCard.jsx  # Kartu prediksi Close (1d, 3d, 7d), Auto Buy/Sell, & Buy/Hold/Sell
│       │   ├── CandlestickChart.jsx# Grafik Candlestick harian + garis target Auto Buy & Auto Sell
│       │   └── Analytics.jsx       # Grafik Aktual vs Prediksi & Tabel Selisih Kesalahan Prediksi
│       └── hooks/
│           └── useRealtimeData.js  # Hook manajemen WebSocket & REST API
│
└── docker-compose.yml              # Orkestrasi container PostgreSQL, Backend API, Worker, dan Frontend Nginx
```

---

## 🚀 Cara Menjalankan Sistem

### 1. Menggunakan Docker Compose (Direkomendasikan)
Pastikan Docker Desktop sudah berjalan, lalu jalankan perintah berikut di direktori utama proyek:

```powershell
docker compose up -d --build
```

Akses layanan melalui browser:
- **Dashboard Web UI:** `http://localhost` atau `http://127.0.0.1`
- **Backend REST API:** `http://localhost:8000`
- **Endpoint Dokumentasi API (Swagger):** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/health`

### 2. Menjalankan Secara Lokal (Tanpa Docker)
1. Pastikan **PostgreSQL** aktif dan atur variabel lingkungan `DATABASE_URL`:
   ```powershell
   $env:DATABASE_URL = "postgresql://eth_predictor:eth_predictor@localhost:5432/eth_predictor"
   ```
2. Jalankan **Backend API** dan **Scheduler Worker**:
   ```powershell
   cd backend1.1
   pip install -r requirements.txt
   python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
   python scheduler\main_runner.py
   ```
3. Jalankan **Frontend React (Vite)**:
   ```powershell
   cd frontend_v1.1
   npm install
   npm run dev
   ```

---

## 🔗 Cara Push ke Repository GitHub (`CryptoTrade-AI`)

```powershell
git remote set-url origin https://github.com/Shdyt13/CryptoTrade-AI.git
git add .
git commit -m "feat: upgrade CryptoTrade AI (ETH & SUI, Daily OHLCV, 1d LSTM, 3d Hybrid LSTM+XGB, 7d Hybrid TCN+XGB)"
git push -u origin main
```

---

**Dikembangkan oleh:** Sapar Hidayat
