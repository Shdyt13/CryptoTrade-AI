import { collection, query, orderBy, limit, getDocs } from 'firebase/firestore';
import { useState, useEffect } from 'react';
import { doc, onSnapshot } from 'firebase/firestore';
import { db } from '../services/firebase';

// Hook 1: Mengambil Harga Real-time
export const useLatestPrice = () => {
  const [priceData, setPriceData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Dengar perubahan di dokumen 'prices/latest'
    const unsub = onSnapshot(doc(db, "prices", "latest"), (doc) => {
      if (doc.exists()) {
        setPriceData(doc.data());
      }
      setLoading(false);
    }, (error) => {
      console.error("Error fetching price:", error);
      setLoading(false);
    });

    return () => unsub(); // Bersihkan listener saat component unmount
  }, []);

  return { priceData, loading };
};

// Hook 2: Mengambil Prediksi Berdasarkan Timeframe
export const usePrediction = (timeframe) => {
  // timeframe bisa '15m', '1h', atau '1w'
  const [predData, setPredData] = useState(null);
  
  useEffect(() => {
    const docName = `latest_${timeframe}`; // e.g., 'latest_15m'
    const unsub = onSnapshot(doc(db, "predictions", docName), (doc) => {
      if (doc.exists()) {
        setPredData(doc.data());
      }
    });

    return () => unsub();
  }, [timeframe]);

  return predData;
};

export const usePredictionHistory = () => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        // Ambil 20 data terakhir dari history_15m
        const q = query(
          collection(db, "history_15m"),
          orderBy("created_at", "desc"),
          limit(20)
        );
        
        const querySnapshot = await getDocs(q);
        const data = [];
        querySnapshot.forEach((doc) => {
          data.push(doc.data());
        });

        // Kita balik urutannya biar grafik jalan dari kiri (lama) ke kanan (baru)
        setHistory(data.reverse()); 
        setLoading(false);
      } catch (error) {
        console.error("Error fetching history:", error);
        setLoading(false);
      }
    };

    fetchHistory();
    // Refresh data setiap 5 menit (opsional)
    const interval = setInterval(fetchHistory, 300000); 
    return () => clearInterval(interval);
  }, []);

  return { history, loading };
};