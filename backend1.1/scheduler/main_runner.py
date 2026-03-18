import time
import schedule
import sys
import os
import traceback
from datetime import datetime

# --- TRIK IMPORT CONFIG (Wajib agar bisa baca modul lain) ---
# Menambahkan folder induk (backend1.1) ke system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Module yang sudah kita buat
from ingestion import fetcher
from predictors import xgb_15m, lstm_1h
from long_term import prophet_forecast
from evaluation import evaluator

def run_safely(job_func, job_name):
    """Wrapper agar jika job error, scheduler TIDAK mati"""
    print(f"\n⏳ [{datetime.now().strftime('%H:%M:%S')}] Starting Job: {job_name}")
    try:
        job_func()
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Finished Job: {job_name}")
    except Exception as e:
        print(f"❌ ERROR in {job_name}: {e}")
        traceback.print_exc() # Print detail error untuk debugging

# --- DEFINISI PEKERJAAN (JOBS) ---

def job_ingest():
    # Ambil harga real-time
    run_safely(lambda: fetcher.get_indodax_price() and fetcher.save_to_firestore(fetcher.get_indodax_price()), "Ingestion Engine")

def job_predict_15m():
    run_safely(xgb_15m.train_and_predict, "XGBoost 15m Predictor")

def job_predict_1h():
    run_safely(lstm_1h.train_and_predict, "LSTM 1h Predictor")

def job_forecast_weekly():
    run_safely(prophet_forecast.train_and_forecast, "Prophet Weekly Forecast")

def job_evaluate():
    # Evaluasi semua timeframe
    run_safely(lambda: evaluator.evaluate_predictions('15m', 'history_15m', 15), "Evaluator 15m")
    run_safely(lambda: evaluator.evaluate_predictions('1h', 'history_1h', 60), "Evaluator 1h")

# --- MAIN LOOP ---

def run_scheduler():
    print("🚀 ETH Predictor v1.1 System STARTED")
    print("   (Tekan Ctrl+C untuk menghentikan system)\n")

    # 1. JALANKAN SEKALI SAAT STARTUP (Agar tidak menunggu jadwal)
    print("⚡ Running startup checks...")
    job_ingest()
    # job_predict_15m() # Opsional: uncomment jika ingin langsung prediksi saat start
    # job_predict_1h()  # Opsional: berat saat startup
    
    # 2. ATUR JADWAL (Schedule)
    
    # Ingest harga setiap 30 detik
    schedule.every(30).seconds.do(job_ingest)
    
    # Prediksi 15 Menit (Setiap menit ke-0, 15, 30, 45)
    # Trik: schedule.every(15).minutes berjalan relatif dari waktu start script.
    # Agar rapi, kita pakai interval biasa dulu.
    schedule.every(15).minutes.do(job_predict_15m)
    
    # Prediksi 1 Jam
    schedule.every(1).hours.do(job_predict_1h)
    
    # Forecast Mingguan (Setiap hari jam 00:00 server)
    schedule.every().day.at("00:00").do(job_forecast_weekly)
    
    # Evaluasi Akurasi (Cek setiap 5 menit)
    schedule.every(5).minutes.do(job_evaluate)

    # 3. LOOP SELAMANYA
    try:
        while True:
            schedule.run_pending()
            time.sleep(1) # Sleep 1 detik agar CPU tidak panas
    except KeyboardInterrupt:
        print("\n🛑 System Stopped by User.")

if __name__ == "__main__":
    run_scheduler()