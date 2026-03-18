import React from 'react';
import { usePrediction } from '../hooks/useRealtimeData';
import { TrendingUp, TrendingDown, Clock, Target } from 'lucide-react';

// Props: title (Judul), timeframe (15m/1h/1w), description (Penjelasan)
const PredictionCard = ({ title, timeframe, description }) => {
  const data = usePrediction(timeframe);

  // Tampilan Loading Skeleton
  if (!data) return (
    <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700 animate-pulse h-48">
      <div className="h-4 bg-slate-700 w-1/3 mb-4 rounded"></div>
      <div className="h-8 bg-slate-700 w-2/3 rounded"></div>
    </div>
  );

  const isBullish = data.signal && data.signal.includes("BULLISH"); // Cek dulu apakah signal ada
  const priceFormatted = data.predicted_price ? data.predicted_price.toLocaleString('id-ID') : "0";
  
  // PERBAIKAN UTAMA: Cek dulu apakah change_percent ada?
  // Jika ada, pakai .toFixed(2). Jika tidak, pakai string "0.00"
  const changePercent = data.change_percent !== undefined ? data.change_percent.toFixed(2) : "0.00";

  return (
    <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-md hover:border-blue-500 transition-colors relative overflow-hidden">
      
      {/* Background Glow Effect */}
      <div className={`absolute top-0 right-0 w-32 h-32 blur-3xl opacity-10 rounded-full ${isBullish ? 'bg-green-500' : 'bg-red-500'}`}></div>

      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-slate-400 font-medium text-sm flex items-center gap-2">
            <Clock size={14} /> {title}
          </h3>
          <p className="text-xs text-slate-600 mt-1">{description}</p>
        </div>
        {/* Badge Signal */}
        <span className={`px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1 ${
          isBullish ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
        }`}>
          {isBullish ? <TrendingUp size={14}/> : <TrendingDown size={14}/>}
          {data.signal}
        </span>
      </div>

      <div className="mt-4">
        <div className="text-xs text-slate-500 mb-1 flex items-center gap-1">
          <Target size={12} /> Target Price
        </div>
        <div className="text-2xl font-bold text-white tracking-wide">
          Rp {priceFormatted}
        </div>
        
        {/* Change Percent */}
        <div className={`text-sm font-medium mt-1 ${isBullish ? 'text-green-400' : 'text-red-400'}`}>
          {isBullish ? '+' : ''}{changePercent}%
          <span className="text-slate-500 text-xs font-normal ml-2">from current</span>
        </div>
      </div>

      {/* Tampilan Khusus Prophet (Range) */}
      {data.lower_bound && (
        <div className="mt-4 pt-4 border-t border-slate-700/50">
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">Min: {(data.lower_bound/1000000).toFixed(1)}jt</span>
            <span className="text-slate-500">Max: {(data.upper_bound/1000000).toFixed(1)}jt</span>
          </div>
          {/* Progress Bar Visual Range */}
          <div className="w-full h-1.5 bg-slate-700 rounded-full mt-1 overflow-hidden">
            <div className="h-full bg-blue-500/50 w-full"></div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PredictionCard;