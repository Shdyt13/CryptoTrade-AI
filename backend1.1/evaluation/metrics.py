import numpy as np

def calculate_mape(y_true, y_pred):
    """
    Mean Absolute Percentage Error (MAPE).
    Seberapa persen rata-rata melesetnya?
    Output: 0.0 sampai 100.0
    """
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    # Hindari pembagian dengan nol
    if np.any(y_true == 0): return 0.0
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

def calculate_direction_accuracy(prev_price, actual_price, predicted_price):
    """
    Apakah arahnya benar? (Directional Accuracy)
    Jika prediksi NAIK dan harga asli NAIK, maka Benar (1).
    """
    # Arah Sebenarnya (1 jika naik, -1 jika turun)
    true_direction = 1 if actual_price > prev_price else -1
    
    # Arah Prediksi
    pred_direction = 1 if predicted_price > prev_price else -1
    
    return 1 if true_direction == pred_direction else 0