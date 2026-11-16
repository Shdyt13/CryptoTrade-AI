import React from 'react';
import { usePrediction } from '../hooks/useRealtimeData';
import {
  TrendingUp,
  TrendingDown,
  CandlestickChart,
  Cpu,
  ArrowDownCircle,
  ArrowUpCircle,
  AlertOctagon,
} from 'lucide-react';
import { CoinLogo } from './CoinIcons';

const DECISION_STYLES = {
  BUY: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
  HOLD: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
  SELL: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
};

const formatFullIdr = (val) => {
  const num = Number(val);
  if (isNaN(num) || num <= 0) return '-';
  return `Rp ${Math.round(num).toLocaleString('id-ID')}`;
};

const PredictionCard = ({ title, timeframe, modelBadge, coin = 'ETH' }) => {
  const data = usePrediction(timeframe, coin);

  if (!data) {
    return (
      <div className="bg-slate-800 p-5 rounded-2xl border border-slate-700 animate-pulse h-64 flex flex-col justify-between">
        <div className="space-y-3">
          <div className="h-4 bg-slate-700 w-1/2 rounded"></div>
          <div className="h-7 bg-slate-700 w-2/3 rounded"></div>
        </div>
        <div className="h-16 bg-slate-700/50 w-full rounded-xl"></div>
      </div>
    );
  }

  if (data.prediction_blocked || data?.data_validation?.valid === false) {
    return (
      <div className="bg-slate-800 p-5 rounded-2xl border border-rose-500/50 flex flex-col justify-between">
        <div>
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-slate-200 font-semibold text-sm flex items-center gap-2">
              <CoinLogo coin={coin} size={18} /> {title}
            </h3>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950/60 text-rose-300 border border-rose-700/60">
              DITANGGUHKAN
            </span>
          </div>
          <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/30 text-xs text-slate-300 flex items-start gap-2">
            <AlertOctagon size={15} className="text-rose-400 shrink-0 mt-0.5" />
            <span>
              {data.reason ||
                data?.data_validation?.reason ||
                'Variabel daily (Open, High, Low, Close, Volume) belum lengkap.'}
            </span>
          </div>
        </div>
      </div>
    );
  }

  const isBullish = typeof data?.signal === 'string' && data.signal.includes('BULLISH');
  const priceFormatted =
    typeof data?.predicted_price === 'number'
      ? Math.round(data.predicted_price).toLocaleString('id-ID')
      : '0';

  let changePercent = '0.00';
  if (typeof data?.change_percent === 'number' && !isNaN(data.change_percent)) {
    changePercent = data.change_percent.toFixed(2);
  } else if (
    typeof data?.predicted_price === 'number' &&
    typeof data?.current_price_at_prediction === 'number' &&
    data.current_price_at_prediction > 0
  ) {
    changePercent = (
      ((data.predicted_price - data.current_price_at_prediction) /
        data.current_price_at_prediction) *
      100
    ).toFixed(2);
  }

  const buyScore = Math.round(Number(data?.buy_score ?? 0));
  const holdScore = Math.round(Number(data?.hold_score ?? 0));
  const sellScore = Math.round(Number(data?.sell_score ?? 0));
  const decision = (data?.decision || (isBullish ? 'BUY' : 'SELL')).toUpperCase();
  const badgeStyle = DECISION_STYLES[decision] || DECISION_STYLES.HOLD;

  const formatWibDate = (val) => {
    if (!val) return '-';
    const d = new Date(val);
    if (isNaN(d.getTime())) return String(val);
    return new Intl.DateTimeFormat('id-ID', {
      timeZone: 'Asia/Jakarta',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(d);
  };

  const targetDateStr = formatWibDate(data?.target_time);

  return (
    <div className="bg-slate-800 p-5 rounded-2xl border border-slate-700 hover:border-blue-500/60 transition-all flex flex-col justify-between">
      <div>
        {/* Baris 1: Icon Koin, Judul Horizon & Target Tanggal */}
        <div className="flex justify-between items-center gap-2 mb-2">
          <h3 className="text-white font-bold text-sm flex items-center gap-2">
            <CoinLogo coin={coin} size={20} className="shrink-0" />
            <span>{title}</span>
          </h3>
          <span className="text-[11px] font-mono text-sky-300 bg-sky-950/50 px-2 py-0.5 rounded border border-sky-800/50">
            Target: {targetDateStr}
          </span>
        </div>

        {/* Baris 2: Nama Model */}
        <div className="text-[11px] text-slate-400 flex items-center gap-1.5 mb-3">
          <Cpu size={12} className="text-indigo-400" />
          <span>{modelBadge || data.model}</span>
        </div>

        {/* Baris 3: Harga Prediksi Close */}
        <div className="bg-slate-900/70 p-3.5 rounded-xl border border-slate-700/60">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="flex items-center gap-1">
              <CandlestickChart size={13} className="text-sky-400" /> Prediksi Close ({coin}/IDR)
            </span>
            <span
              className={`font-bold flex items-center gap-1 ${
                Number(changePercent) >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {isBullish ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
              {Number(changePercent) >= 0 ? '+' : ''}
              {changePercent}%
            </span>
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            Rp {priceFormatted}
          </div>
        </div>

        {/* Baris 4: Acuan Auto Buy & Auto Sell */}
        <div className="mt-3 grid grid-cols-2 gap-2">
          <div className="bg-slate-900/50 border border-amber-500/30 rounded-xl p-2.5">
            <div className="text-[10px] text-amber-300 font-semibold flex items-center gap-1">
              <ArrowDownCircle size={11} /> Auto Buy
            </div>
            <div className="text-xs font-bold text-white font-mono mt-0.5">
              {formatFullIdr(data.auto_buy_price)}
            </div>
          </div>

          <div className="bg-slate-900/50 border border-emerald-500/30 rounded-xl p-2.5">
            <div className="text-[10px] text-emerald-300 font-semibold flex items-center gap-1">
              <ArrowUpCircle size={11} /> Auto Sell
            </div>
            <div className="text-xs font-bold text-white font-mono mt-0.5">
              {formatFullIdr(data.auto_sell_price)}
            </div>
          </div>
        </div>
      </div>

      {/* Baris 5: Saran Keputusan Buy / Hold / Sell */}
      <div className="mt-4 pt-3 border-t border-slate-700/60">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-slate-400">Saran Keputusan:</span>
          <span className={`px-2.5 py-0.5 rounded text-xs font-bold border ${badgeStyle}`}>
            {decision}
          </span>
        </div>

        <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden flex my-2">
          <div style={{ width: `${buyScore}%` }} className="bg-emerald-500 h-full" />
          <div style={{ width: `${holdScore}%` }} className="bg-amber-400 h-full" />
          <div style={{ width: `${sellScore}%` }} className="bg-rose-500 h-full" />
        </div>

        <div className="flex justify-between text-[11px] font-mono text-slate-300">
          <span className="text-emerald-400">Buy {buyScore}%</span>
          <span className="text-amber-300">Hold {holdScore}%</span>
          <span className="text-rose-400">Sell {sellScore}%</span>
        </div>
      </div>
    </div>
  );
};

export default PredictionCard;
