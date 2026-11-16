import React, { useState } from 'react';
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
  Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { CheckCircle, AlertTriangle, TrendingUp, Table2 } from 'lucide-react';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const HORIZON_OPTIONS = [
  { id: '1d', label: '1 Hari (LSTM)' },
  { id: '3d', label: '3 Hari (Hybrid LSTM+XGB)' },
  { id: '7d', label: '7 Hari (Hybrid TCN+XGB)' },
];

const Analytics = ({ coin = 'ETH' }) => {
  const [selectedTimeframe, setSelectedTimeframe] = useState('1d');
  const coinKey = (coin || 'ETH').toUpperCase();

  const { history: allHistory, loading: loadingAll } = usePredictionHistory(
    selectedTimeframe,
    coinKey,
    false,
    40
  );

  const processDate = (inputDate) => {
    if (!inputDate) return new Date();
    if (typeof inputDate.toDate === 'function') return inputDate.toDate();
    const d = new Date(inputDate);
    return isNaN(d.getTime()) ? new Date() : d;
  };

  const safeAllHistory = Array.isArray(allHistory) ? allHistory : [];

  const toWibDateKey = (dateInput) => {
    const d = processDate(dateInput);
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Jakarta',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).formatToParts(d);
    const y = parts.find((p) => p.type === 'year')?.value;
    const m = parts.find((p) => p.type === 'month')?.value;
    const day = parts.find((p) => p.type === 'day')?.value;
    return `${y}-${m}-${day}`;
  };

  const formatWibDateLabel = (dateInput) => {
    const d = processDate(dateInput);
    return new Intl.DateTimeFormat('id-ID', {
      timeZone: 'Asia/Jakarta',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(d);
  };

  const todayWibKey = toWibDateKey(new Date());

  // Hanya tampilkan data yang SUDAH memiliki aktual DAN tanggal targetnya SUDAH TUTUP (< hari ini WIB)
  const rawEvaluated = safeAllHistory.filter((item) => {
    if (
      !item ||
      !item.evaluated ||
      typeof item.actual_price !== 'number' ||
      isNaN(item.actual_price) ||
      typeof item.predicted_price !== 'number' ||
      isNaN(item.predicted_price)
    ) {
      return false;
    }
    const targetKey = toWibDateKey(item.target_time || item.created_at);
    return targetKey < todayWibKey;
  });

  const dedupMap = new Map();
  rawEvaluated.forEach((item) => {
    const key = toWibDateKey(item.target_time || item.created_at);
    dedupMap.set(key, item);
  });
  const evaluatedData = Array.from(dedupMap.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map((entry) => entry[1]);

  const labels = evaluatedData.map((item) =>
    formatWibDateLabel(item.target_time || item.created_at)
  );

  const actualVsPredChartData = {
    labels,
    datasets: [
      {
        label: `Harga Aktual Close (${coinKey}/IDR)`,
        data: evaluatedData.map((item) => item.actual_price),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.12)',
        pointBackgroundColor: '#10b981',
        pointRadius: 3.5,
        borderWidth: 2.5,
        fill: true,
        tension: 0.3,
      },
      {
        label: `Harga Prediksi Close (${selectedTimeframe.toUpperCase()})`,
        data: evaluatedData.map((item) => item.predicted_price),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.08)',
        pointBackgroundColor: '#3b82f6',
        pointRadius: 3.5,
        borderWidth: 2.5,
        borderDash: [5, 4],
        fill: false,
        tension: 0.3,
      },
    ],
  };

  const actualVsPredOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { position: 'top', labels: { color: '#cbd5e1', font: { size: 12 } } },
      tooltip: {
        callbacks: {
          afterBody: (items) => {
            if (!items || items.length === 0) return '';
            const row = evaluatedData[items[0].dataIndex];
            if (!row) return '';
            const act = Number(row.actual_price);
            const pred = Number(row.predicted_price);
            const absDiff = Math.abs(pred - act);
            const pct = act > 0 ? (absDiff / act) * 100 : 0;
            return `Selisih Kesalahan: Rp ${Math.round(absDiff).toLocaleString('id-ID')} (${pct.toFixed(2)}%)`;
          },
        },
      },
    },
    scales: {
      y: {
        grid: { color: '#1e293b' },
        ticks: {
          color: '#94a3b8',
          callback: (val) => `Rp ${Number(val).toLocaleString('id-ID')}`,
        },
      },
      x: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8', maxRotation: 30 } },
    },
  };

  const pendingRows = safeAllHistory.filter((item) => {
    const targetKey = toWibDateKey(item.target_time || item.created_at);
    return targetKey >= todayWibKey || !item.evaluated || item.actual_price == null;
  });
  const latestPending = pendingRows.length > 0 ? [pendingRows[pendingRows.length - 1]] : [];
  const tableRows = [...evaluatedData, ...latestPending].reverse().slice(0, 15);

  return (
    <div className="space-y-6">
      {/* Bagian 1: Grafik Aktual vs Prediksi */}
      <div className="bg-slate-800 p-5 rounded-2xl border border-slate-700">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-4 border-b border-slate-700/70 mb-4">
          <div>
            <h2 className="text-base md:text-lg font-bold text-white flex items-center gap-2">
              <TrendingUp className="text-emerald-400" size={20} />
              Grafik Harga Aktual vs Prediksi ({coinKey}/IDR)
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Menampilkan perbandingan harga Close aktual (s/d {labels.length > 0 ? labels[labels.length - 1] : 'Kemarin'}) terhadap hasil prediksi model.
            </p>
          </div>

          <div className="flex bg-slate-900 p-1 rounded-xl border border-slate-700 self-start md:self-auto">
            {HORIZON_OPTIONS.map((h) => (
              <button
                key={h.id}
                onClick={() => setSelectedTimeframe(h.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  selectedTimeframe === h.id
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {h.label}
              </button>
            ))}
          </div>
        </div>

        {loadingAll ? (
          <div className="h-72 flex items-center justify-center text-slate-400 animate-pulse">
            Memuat grafik aktual vs prediksi...
          </div>
        ) : evaluatedData.length === 0 ? (
          <div className="h-56 flex flex-col items-center justify-center text-slate-400 bg-slate-900/50 rounded-xl border border-slate-700/60 p-6 text-center">
            <AlertTriangle size={24} className="text-amber-400 mb-2" />
            <p className="text-xs text-slate-300">
              Belum ada data prediksi pada horizon {selectedTimeframe.toUpperCase()} yang memiliki nilai aktual.
            </p>
          </div>
        ) : (
          <div className="h-72">
            <Line data={actualVsPredChartData} options={actualVsPredOptions} />
          </div>
        )}
      </div>

      {/* Bagian 2: Tabel Selisih Kesalahan Prediksi Sebelumnya Berdasarkan Data Aktual */}
      <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
        <div className="p-5 border-b border-slate-700">
          <h3 className="font-bold text-white text-base flex items-center gap-2">
            <Table2 size={18} className="text-blue-400" />
            Tabel Selisih Kesalahan Prediksi Berdasarkan Data Aktual ({coinKey}/IDR — {selectedTimeframe.toUpperCase()})
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Daftar perbandingan harga Prediksi Close dan Aktual Close beserta besar selisih kesalahannya.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs md:text-sm text-slate-300">
            <thead className="bg-slate-900 text-slate-400 uppercase font-semibold text-xs">
              <tr>
                <th className="px-4 py-3">Tanggal Target</th>
                <th className="px-4 py-3">Prediksi Close</th>
                <th className="px-4 py-3">Aktual Close</th>
                <th className="px-4 py-3">Selisih Kesalahan (Rp)</th>
                <th className="px-4 py-3">Selisih (%)</th>
                <th className="px-4 py-3">Keputusan</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/60">
              {tableRows.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-6 py-6 text-center text-slate-500">
                    Belum ada riwayat prediksi untuk {coinKey} ({selectedTimeframe}).
                  </td>
                </tr>
              ) : (
                tableRows.map((item, index) => {
                  const targetKey = toWibDateKey(item.target_time || item.created_at);
                  const isDayClosed = targetKey < todayWibKey;
                  const predPrice =
                    typeof item.predicted_price === 'number'
                      ? Math.round(item.predicted_price).toLocaleString('id-ID')
                      : '-';
                  const hasActual =
                    isDayClosed &&
                    Boolean(item.evaluated) &&
                    typeof item.actual_price === 'number' &&
                    !isNaN(item.actual_price);
                  const actualPrice = hasActual
                    ? Math.round(item.actual_price).toLocaleString('id-ID')
                    : null;

                  const signedDiff = hasActual
                    ? Number(item.predicted_price) - Number(item.actual_price)
                    : null;
                  const absDiff = hasActual ? Math.abs(signedDiff) : null;
                  const pctDiff =
                    hasActual && Number(item.actual_price) !== 0
                      ? (absDiff / Number(item.actual_price)) * 100
                      : null;

                  const dec = (item.decision || 'HOLD').toUpperCase();

                  return (
                    <tr key={item.id || index} className="hover:bg-slate-700/30">
                      <td className="px-4 py-3 whitespace-nowrap text-white font-medium">
                        {formatWibDateLabel(item.target_time || item.created_at)}
                      </td>
                      <td className="px-4 py-3 text-blue-400 font-semibold font-mono whitespace-nowrap">
                        Rp {predPrice}
                      </td>
                      <td className="px-4 py-3 text-emerald-400 font-semibold font-mono whitespace-nowrap">
                        {actualPrice ? (
                          `Rp ${actualPrice}`
                        ) : (
                          <span className="text-slate-500 font-sans">Belum Close</span>
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono whitespace-nowrap">
                        {absDiff != null ? (
                          <span className="text-amber-300 font-semibold">
                            Rp {Math.round(absDiff).toLocaleString('id-ID')}
                          </span>
                        ) : (
                          <span className="text-slate-500">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono whitespace-nowrap">
                        {pctDiff != null ? (
                          <span className="text-slate-200 font-semibold">
                            {pctDiff.toFixed(2)}%
                          </span>
                        ) : (
                          <span className="text-slate-500">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                            dec === 'BUY'
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : dec === 'SELL'
                              ? 'bg-rose-500/20 text-rose-300'
                              : 'bg-amber-500/20 text-amber-300'
                          }`}
                        >
                          {dec}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {!hasActual ? (
                          <span className="inline-flex items-center gap-1 text-amber-400 text-xs">
                            <AlertTriangle size={13} /> Menunggu Aktual
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-emerald-400 text-xs">
                            <CheckCircle size={13} /> Selesai
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
