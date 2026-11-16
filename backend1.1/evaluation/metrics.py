import numpy as np


def calculate_mape(y_true, y_pred) -> float:
    """
    Mean Absolute Percentage Error (MAPE).
    Output: persentase (0.0 sampai 100.0+)
    """
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    if np.any(y_true_arr == 0):
        return 0.0
    return float(np.mean(np.abs((y_true_arr - y_pred_arr) / y_true_arr)) * 100.0)


def calculate_mae(y_true, y_pred) -> float:
    """
    Mean Absolute Error (MAE) dalam satuan harga (IDR).
    """
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true_arr - y_pred_arr)))


def calculate_rmse(y_true, y_pred) -> float:
    """
    Root Mean Squared Error (RMSE) dalam satuan harga (IDR).
    """
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean(np.square(y_true_arr - y_pred_arr))))


def calculate_direction_accuracy(prev_price, actual_price, predicted_price) -> int:
    """
    Apakah arah pergerakan harga benar? (Directional Accuracy)
    Jika prediksi NAIK dan harga asli NAIK (atau sama-sama TURUN), maka Benar (1).
    """
    true_direction = 1 if actual_price >= prev_price else -1
    pred_direction = 1 if predicted_price >= prev_price else -1
    return 1 if true_direction == pred_direction else 0
