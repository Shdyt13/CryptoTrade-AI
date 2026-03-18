import React from 'react';
import { useLatestPrice } from '../hooks/useRealtimeData';
import { ArrowUp, ArrowDown, Activity } from 'lucide-react';

const PriceTicker = () => {
  const { priceData, loading } = useLatestPrice();

  if (loading) return <div className="animate-pulse h-20 bg-gray-800 rounded-xl"></div>;
  if (!priceData) return <div className="text-red-400">Connection Error</div>;

  // Hitung perubahan harga (Dummy calculation jika tidak ada data history kemarin)
  // Di real production, kita bandingkan dengan harga open 24h
  const isUp = true; // Sementara default hijau

  return (
    <div className="bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-lg flex justify-between items-center mb-6">
      <div>
        <h2 className="text-slate-400 text-sm font-medium mb-1 flex items-center gap-2">
          <Activity size={16} className="text-blue-400"/> Live Market (Indodax)
        </h2>
        <div className="text-4xl font-bold text-white tracking-tight">
          Rp {priceData.price.toLocaleString('id-ID')}
        </div>
      </div>
      
      <div className="text-right">
        <div className="text-xs text-slate-500 mb-1">24h Volume</div>
        <div className="text-slate-300 font-mono">
          IDR {(priceData.volume / 1000000000).toFixed(2)} M
        </div>
        <div className="text-xs text-slate-500 mt-2">Last Update: {new Date().toLocaleTimeString()}</div>
      </div>
    </div>
  );
};

export default PriceTicker;