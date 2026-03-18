import React from 'react';
import { usePredictionHistory } from '../hooks/useRealtimeData';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

// Registrasi komponen ChartJS
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const Analytics = () => {
  const { history, loading } = usePredictionHistory();

  if (loading) return <div className="text-white p-10">Loading Data Analysis...</div>;

  // --- FUNGSI BANTUAN: KONVERSI TANGGAL ---
  // Fungsi ini bertugas mendeteksi apakah data tanggal berupa Firestore Timestamp atau String biasa
  const processDate = (inputDate) => {
    if (!inputDate) return new Date();
    // Cek apakah ini objek Timestamp dari Firestore (punya fungsi .toDate)
    if (typeof inputDate.toDate === 'function') {
      return inputDate.toDate();
    }
    // Jika bukan, anggap string/number biasa
    return new Date(inputDate);
  };

  // --- PERSIAPAN DATA GRAFIK ---
  const labels = history.map(item => {
    const date = processDate(item.created_at);
    // Format Jam:Menit (contoh: 14:05)
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  });

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Harga Asli (Real)',
        data: history.map(item => item.actual_price || null), // Null jika belum ada harga asli
        borderColor: '#10b981', // Hijau
        backgroundColor: '#10b981',
        tension: 0.4,
      },
      {
        label: 'Harga Prediksi AI',
        data: history.map(item => item.predicted_price),
        borderColor: '#3b82f6', // Biru
        backgroundColor: '#3b82f6',
        borderDash: [5, 5], // Garis putus-putus
        tension: 0.4,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { position: 'top', labels: { color: '#cbd5e1' } },
      title: { display: true, text: 'Perbandingan Real vs Prediksi (15 Menit Terakhir)', color: '#94a3b8' },
    },
    scales: {
      y: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
      x: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
    },
  };

  return (
    <div className="text-slate-200">
      <h2 className="text-2xl font-bold mb-6">Analisis Akurasi Model</h2>

      {/* BAGIAN GRAFIK */}
      <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-lg mb-8">
        <Line data={chartData} options={options} />
      </div>

      {/* BAGIAN TABEL DATA */}
      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        <div className="p-6 border-b border-slate-700">
          <h3 className="font-bold">Log Evaluasi Detail</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-400">
            <thead className="bg-slate-900 text-slate-200 uppercase font-medium">
              <tr>
                <th className="px-6 py-4">Waktu</th>
                <th className="px-6 py-4">Prediksi</th>
                <th className="px-6 py-4">Realita</th>
                <th className="px-6 py-4">Error Rate (MAPE)</th>
                <th className="px-6 py-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {history.slice().reverse().map((item, index) => (
                <tr key={index} className="hover:bg-slate-700/50">
                  <td className="px-6 py-4">
                    {/* Gunakan fungsi processDate agar tabel juga aman dari error */}
                    {processDate(item.created_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-blue-400">Rp {item.predicted_price.toLocaleString()}</td>
                  <td className="px-6 py-4 text-green-400">
                    {item.actual_price ? `Rp ${item.actual_price.toLocaleString()}` : '-'}
                  </td>
                  <td className="px-6 py-4 font-mono">
                    {item.error_rate ? `${item.error_rate.toFixed(4)}%` : <span className="text-slate-600">Waiting...</span>}
                  </td>
                  <td className="px-6 py-4">
                    {!item.actual_price ? (
                      <span className="flex items-center gap-1 text-yellow-500"><AlertTriangle size={14}/> Pending</span>
                    ) : item.error_rate < 1.0 ? (
                      <span className="flex items-center gap-1 text-green-500"><CheckCircle size={14}/> Akurat</span>
                    ) : (
                      <span className="flex items-center gap-1 text-red-500"><XCircle size={14}/> Meleset</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Analytics;