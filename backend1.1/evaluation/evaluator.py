import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import pytz

# --- TRIK IMPORT CONFIG ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import db
from evaluation.metrics import calculate_mape, calculate_direction_accuracy

def get_closest_price(target_time):
    """
    Mencari harga asli (Actual Price) di database 'prices'
    yang waktunya paling dekat dengan target_time.
    """
    try:
        # Cari harga di range waktu target_time +/- 2 menit
        start_time = target_time - timedelta(minutes=2)
        end_time = target_time + timedelta(minutes=2)
        
        # Query Firestore (Perlu index composite di production, tapi untuk dev ok)
        # Kita ambil manual semua harga di range itu (biasanya cuma 1-3 data)
        # Karena query range string ISO agak tricky, kita fetch data terbaru aja
        # lalu filter di python (untuk simpelnya)
        
        # STRATEGI SIMPEL: Ambil dokumen harga yang ID-nya (timestamp) mirip
        # Format ID kita: ISO String.
        # Kita coba cari dokumen persis dulu, kalau gak ada cari range.
        
        # Untuk v1.1 ini, kita pakai logika: 
        # Ambil harga 'latest' JIKA waktu update-nya sudah lewat target_time
        # (Ini asumsi evaluator jalan real-time)
        
        # TAPI yang benar: Query collection 'prices'
        # Convert datetime ke string ISO format YYYY-MM-DD
        prefix = target_time.strftime('%Y-%m-%d')
        
        docs = db.collection('prices').where('timestamp', '>=', start_time).where('timestamp', '<=', end_time).stream()
        
        closest_doc = None
        min_diff = float('inf')
        
        for doc in docs:
            data = doc.to_dict()
            # Timestamp di firestore bisa jadi object datetime
            price_time = data['timestamp']
            
            # Hitung selisih detik
            diff = abs((price_time - target_time).total_seconds())
            if diff < min_diff:
                min_diff = diff
                closest_doc = data
                
        return closest_doc
        
    except Exception as e:
        print(f"⚠️ Error finding price: {e}")
        return None

def evaluate_predictions(timeframe, collection_name, duration_minutes):
    print(f"⚖️ Evaluating {timeframe} Model...")
    
    # 1. Ambil history prediksi yang BELUM dievaluasi
    # Batasi 10 terakhir agar tidak berat
    preds_ref = db.collection(collection_name).where('evaluated', '==', False).limit(10)
    preds = preds_ref.stream()
    
    evaluated_count = 0
    total_mape = 0
    correct_direction = 0
    
    for doc in preds:
        p_data = doc.to_dict()
        
        # Kapan prediksi ini dibuat?
        created_at = p_data['created_at'] # Datetime object w/ timezone
        
        # Kapan target prediksinya? (Created + Durasi)
        target_time = created_at + timedelta(minutes=duration_minutes)
        
        # Cek apakah sekarang sudah melewati waktu target?
        now = datetime.now(pytz.utc)
        if now < target_time:
            # Belum waktunya dinilai (masih masa depan)
            continue
            
        # 2. Cari Kunci Jawaban (Harga Asli pada Target Time)
        actual_data = get_closest_price(target_time)
        
        if actual_data:
            actual_price = actual_data['price']
            predicted_price = p_data['predicted_price']
            prev_price = p_data['current_price_at_prediction'] # Harga saat prediksi dibuat
            
            # 3. Hitung Nilai
            mape = calculate_mape(actual_price, predicted_price)
            is_correct = calculate_direction_accuracy(prev_price, actual_price, predicted_price)
            
            # 4. Update Rapor di Dokumen Prediksi
            doc.reference.update({
                'actual_price': actual_price,
                'error_mape': mape,
                'direction_correct': bool(is_correct),
                'evaluated': True,
                'evaluated_at': now
            })
            
            print(f"   ✅ Graded: Pred {predicted_price:,.0f} vs Act {actual_price:,.0f} | Error: {mape:.2f}%")
            
            evaluated_count += 1
            total_mape += mape
            correct_direction += is_correct
        else:
            print(f"   ⏳ No actual price data yet for {target_time}")

    # 5. Update Statistik Global (Opsional: Rata-rata hari ini)
    if evaluated_count > 0:
        avg_mape = total_mape / evaluated_count
        accuracy_rate = (correct_direction / evaluated_count) * 100
        print(f"📊 Batch Result: Avg Error {avg_mape:.2f}% | Direction Accuracy {accuracy_rate:.0f}%")
        
        # Simpan ke 'accuracy/stats'
        stats_ref = db.collection('accuracy').document(f'stats_{timeframe}')
        stats_ref.set({
            'last_updated': datetime.now(),
            'current_mape': avg_mape,
            'current_accuracy': accuracy_rate,
            'samples': evaluated_count
        }, merge=True)

if __name__ == "__main__":
    # Test Evaluasi Manual
    # Catatan: Ini mungkin tidak akan menilai apapun jika belum ada prediksi lama yang "matang"
    # Karena prediksi yang baru kita buat tadi targetnya masih 15 menit/1 jam lagi dari sekarang.
    evaluate_predictions('15m', 'history_15m', 15)
    evaluate_predictions('1h', 'history_1h', 60)