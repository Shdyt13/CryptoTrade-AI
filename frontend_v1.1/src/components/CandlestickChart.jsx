import React, { useState, useMemo } from 'react';
import { useDailyCandles, usePrediction } from '../hooks/useRealtimeData';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import {
  CandlestickChart as CandleIcon,
  CheckCircle2,
  AlertOctagon,
} from 'lucide-react';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const HORIZONS = [
  { id: '1d', label: '1 Hari (LSTM)' },
  { id: '3d', label: '3 Hari (Hybrid LSTM+XGB)' },
  { id: '7d', label: '7 Hari (Hybrid TCN+XGB)' },
];

const formatIdr = (val) => {
  const num = Number(val);
  if (isNaN(num) || num <= 0) return '-';
  return `Rp ${Math.round(num).toLocaleString('id-ID')}`;
};

const CandlestickChart = ({ coin = 'ETH' }) => {
  const [selectedHorizon, setSelectedHorizon] = useState('1d');
  const coinKey = (coin || 'ETH').toUpperCase();

  const { candles, validation, loading } = useDailyCandles(coinKey, 35);
  const activePred = usePrediction(selectedHorizon, coinKey);

  const lastCandle = candles.length > 0 ? candles[candles.length - 1] : null;
  const isDataValid = validation ? Boolean(validation.valid) : candles.length >= 14;

  const formatWibShort = (tsOrDate) => {
    if (!tsOrDate) return '';
    const d = new Date(tsOrDate);
    if (isNaN(d.getTime())) return String(tsOrDate);
    return new Intl.DateTimeFormat('id-ID', {
      timeZone: 'Asia/Jakarta',
      day: '2-digit',
      month: 'short',
    }).format(d);
  };

  const lastClosedLabel = lastCandle
    ? formatWibShort(lastCandle.timestamp || lastCandle.wib_date)
    : '-';
  const targetPredLabel =
    activePred && activePred.target_time ? formatWibShort(activePred.target_time) : '';

  const labels = useMemo(() => {
    const histLabels = candles.map((c) => formatWibShort(c.timestamp || c.wib_date));
    if (activePred && !activePred.prediction_blocked && activePred.predicted_price) {
      histLabels.push(`Target ${targetPredLabel || selectedHorizon.toUpperCase()}`);
    }
    return histLabels;
  }, [candles, activePred, selectedHorizon, targetPredLabel]);

  const chartData = useMemo(() => {
    const hasProj = Boolean(
      activePred && !activePred.prediction_blocked && activePred.predicted_price
    );
    const totalLen = candles.length + (hasProj ? 1 : 0);

    const bodyData = candles.map((c) => {
      const o = Number(c.open);
      const cl = Number(c.close);
      if (Math.abs(cl - o) < o * 0.0008) {
        const eps = o * 0.0008;
        return [o - eps, cl + eps];
      }
      return [Math.min(o, cl), Math.max(o, cl)];
    });

    const bgColors = candles.map((c) =>
      Number(c.close) >= Number(c.open)
        ? 'rgba(16, 185, 129, 0.85)'
        : 'rgba(244, 63, 94, 0.85)'
    );
    const borderColors = candles.map((c) =>
      Number(c.close) >= Number(c.open) ? '#10b981' : '#f43f5e'
    );

    if (hasProj && lastCandle) {
      const lastClose = Number(lastCandle.close);
      const predClose = Number(activePred.predicted_price);
      bodyData.push([Math.min(lastClose, predClose), Math.max(lastClose, predClose)]);
      bgColors.push('rgba(59, 130, 246, 0.55)');
      borderColors.push('#60a5fa');
    }

    const predCloseVal = hasProj ? Number(activePred.predicted_price) : null;
    const autoBuyVal = hasProj ? Number(activePred.auto_buy_price) : null;
    const autoSellVal = hasProj ? Number(activePred.auto_sell_price) : null;

    const datasets = [
      {
        type: 'bar',
        label: `Candlestick Harian (${coinKey}/IDR)`,
        data: bodyData,
        backgroundColor: bgColors,
        borderColor: borderColors,
        borderWidth: 1.5,
        borderSkipped: false,
        barPercentage: 0.68,
        categoryPercentage: 0.82,
        rawCandles: candles,
        projectedCandle:
          hasProj && lastCandle
            ? {
                open: Number(lastCandle.close),
                close: predCloseVal,
                high: Math.max(Number(lastCandle.close), predCloseVal, autoSellVal || 0),
                low: Math.min(Number(lastCandle.close), predCloseVal, autoBuyVal || Infinity),
                isProjection: true,
              }
            : null,
        order: 2,
      },
    ];

    if (predCloseVal) {
      datasets.push({
        type: 'line',
        label: `Prediksi Close: ${formatIdr(predCloseVal)}`,
        data: Array(totalLen).fill(predCloseVal),
        borderColor: '#38bdf8',
        borderWidth: 2,
        borderDash: [6, 4],
        pointRadius: (ctx) => (ctx.dataIndex === totalLen - 1 ? 5 : 0),
        pointBackgroundColor: '#38bdf8',
        fill: false,
        order: 1,
      });
    }

    if (autoSellVal) {
      datasets.push({
        type: 'line',
        label: `Auto Sell: ${formatIdr(autoSellVal)}`,
        data: Array(totalLen).fill(autoSellVal),
        borderColor: '#10b981',
        borderWidth: 1.8,
        borderDash: [4, 4],
        pointRadius: 0,
        fill: false,
        order: 1,
      });
    }

    if (autoBuyVal) {
      datasets.push({
        type: 'line',
        label: `Auto Buy: ${formatIdr(autoBuyVal)}`,
        data: Array(totalLen).fill(autoBuyVal),
        borderColor: '#f59e0b',
        borderWidth: 1.8,
        borderDash: [4, 4],
        pointRadius: 0,
        fill: false,
        order: 1,
      });
    }

    return { labels, datasets };
  }, [candles, labels, activePred, coinKey, lastCandle]);

  const candlestickWickPlugin = useMemo(
    () => ({
      id: 'candlestickWickPlugin',
      afterDatasetsDraw(chart) {
        const { ctx, scales } = chart;
        const yScale = scales.y;
        const meta = chart.getDatasetMeta(0);
        const dataset = chart.data.datasets[0];
        if (!meta || !dataset || !yScale) return;

        const rawCandles = dataset.rawCandles || [];
        const proj = dataset.projectedCandle;

        ctx.save();
        meta.data.forEach((barElement, index) => {
          const candle = index < rawCandles.length ? rawCandles[index] : proj;
          if (!candle) return;

          const highY = yScale.getPixelForValue(Number(candle.high));
          const lowY = yScale.getPixelForValue(Number(candle.low));
          const x = barElement.x;

          const isBull = Number(candle.close) >= Number(candle.open);
          ctx.strokeStyle = candle.isProjection
            ? '#60a5fa'
            : isBull
            ? '#10b981'
            : '#f43f5e';
          ctx.lineWidth = candle.isProjection ? 2 : 1.5;
          ctx.setLineDash(candle.isProjection ? [3, 3] : []);

          ctx.beginPath();
          ctx.moveTo(x, highY);
          ctx.lineTo(x, lowY);
          ctx.stroke();
        });
        ctx.restore();
      },
    }),
    []
  );

  const yBounds = useMemo(() => {
    if (candles.length === 0) return {};
    const lows = candles.map((c) => Number(c.low)).filter((v) => v > 0);
    const highs = candles.map((c) => Number(c.high)).filter((v) => v > 0);
    if (activePred && !activePred.prediction_blocked) {
      ['predicted_price', 'auto_buy_price', 'auto_sell_price'].forEach((k) => {
        const v = Number(activePred[k]);
        if (v > 0) {
          lows.push(v);
          highs.push(v);
        }
      });
    }
    const minVal = Math.min(...lows);
    const maxVal = Math.max(...highs);
    const pad = (maxVal - minVal) * 0.08 || minVal * 0.02;
    return {
      min: Math.max(0, Math.floor(minVal - pad)),
      max: Math.ceil(maxVal + pad),
    };
  }, [candles, activePred]);

  const chartOptions = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          position: 'top',
          labels: { color: '#cbd5e1', font: { size: 11 }, usePointStyle: true },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              if (ctx.datasetIndex === 0) {
                const rawList = ctx.dataset.rawCandles || [];
                const idx = ctx.dataIndex;
                if (idx < rawList.length) {
                  const c = rawList[idx];
                  return [
                    `Open: ${formatIdr(c.open)}`,
                    `High: ${formatIdr(c.high)}`,
                    `Low: ${formatIdr(c.low)}`,
                    `Close: ${formatIdr(c.close)}`,
                    `Volume: ${Number(c.volume || 0).toLocaleString('id-ID', {
                      maximumFractionDigits: 2,
                    })}`,
                  ];
                }
                if (ctx.dataset.projectedCandle) {
                  return `Prediksi Close: ${formatIdr(ctx.dataset.projectedCandle.close)}`;
                }
              }
              return `${ctx.dataset.label}`;
            },
          },
        },
      },
      scales: {
        y: {
          min: yBounds.min,
          max: yBounds.max,
          grid: { color: '#1e293b' },
          ticks: {
            color: '#94a3b8',
            callback: (val) => `Rp ${Number(val).toLocaleString('id-ID')}`,
          },
        },
        x: {
          grid: { color: '#1e293b' },
          ticks: { color: '#94a3b8', maxRotation: 30 },
        },
      },
    }),
    [yBounds]
  );

  return (
    <div className="bg-slate-800 p-5 rounded-2xl border border-slate-700 mb-8">
      {/* Header Ringkas */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-4 border-b border-slate-700/70">
        <div>
          <h2 className="text-base md:text-lg font-bold text-white flex items-center gap-2">
            <CandleIcon className="text-emerald-400" size={20} />
            Grafik Candlestick Harian & Strategi Auto Buy / Auto Sell ({coinKey}/IDR)
          </h2>
          <div className="flex flex-wrap items-center gap-2 mt-1 text-xs">
            {isDataValid ? (
              <span className="text-emerald-400 flex items-center gap-1 font-medium">
                <CheckCircle2 size={13} /> Variabel Daily (Open, High, Low, Close, Volume) Lengkap s/d {lastClosedLabel}
              </span>
            ) : (
              <span className="text-rose-400 flex items-center gap-1 font-medium">
                <AlertOctagon size={13} /> Variabel Daily Belum Lengkap — Prediksi Ditangguhkan
              </span>
            )}
          </div>
        </div>

        <div className="flex bg-slate-900 p-1 rounded-xl border border-slate-700 self-start md:self-auto">
          {HORIZONS.map((h) => (
            <button
              key={h.id}
              onClick={() => setSelectedHorizon(h.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                selectedHorizon === h.id
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {h.label}
            </button>
          ))}
        </div>
      </div>

      {/* Area Chart */}
      {loading ? (
        <div className="h-80 flex items-center justify-center text-slate-400 animate-pulse">
          Memuat grafik candlestick harian...
        </div>
      ) : !isDataValid ? (
        <div className="mt-4 p-6 rounded-xl bg-rose-950/30 border border-rose-500/40 text-center">
          <p className="text-xs text-slate-300">
            Data harian belum memiliki seluruh variabel wajib (<b>open, high, low, close, volume</b>). Prediksi belum dapat dilakukan.
          </p>
        </div>
      ) : (
        <div className="h-80 mt-4">
          <Bar
            key={`${coinKey}-${selectedHorizon}`}
            data={chartData}
            options={chartOptions}
            plugins={[candlestickWickPlugin]}
          />
        </div>
      )}
    </div>
  );
};

export default CandlestickChart;
