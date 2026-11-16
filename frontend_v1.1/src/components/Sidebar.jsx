import React from 'react';
import { CandlestickChart, Layers, TrendingUp } from 'lucide-react';
import { TradingLogoIcon, CoinLogo } from './CoinIcons';

const Sidebar = ({ selectedCoin = 'ETH', onSelectCoin }) => {
  const coins = [
    { code: 'ETH', name: 'Ethereum', pair: 'ETH/IDR' },
    { code: 'SUI', name: 'Sui Network', pair: 'SUI/IDR' },
  ];

  return (
    <div className="w-60 bg-slate-900 border-r border-slate-800 min-h-screen p-4 flex-col fixed left-0 top-0 hidden md:flex z-20">
      {/* Logo Sistem Bertema Trading */}
      <div className="flex items-center gap-3 mb-7 px-1.5">
        <TradingLogoIcon size={38} className="shrink-0 shadow-lg shadow-blue-900/30 rounded-xl" />
        <div>
          <h1 className="font-bold text-white text-sm leading-tight tracking-wide">
            CryptoTrade AI
          </h1>
          <p className="text-[11px] text-emerald-400 font-medium flex items-center gap-1 mt-0.5">
            <TrendingUp size={11} /> Daily OHLCV Trading
          </p>
        </div>
      </div>

      {/* Menu Utama */}
      <div className="mb-6">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2 px-2">
          Menu Trading
        </div>
        <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-xs bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold shadow-md shadow-blue-900/30">
          <CandlestickChart size={16} />
          <span>Dashboard Trading</span>
        </div>
      </div>

      {/* Pilih Koin dengan Icon Logo Resmi ETH & SUI */}
      <div className="mb-6">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2 px-2">
          Pilih Aset Koin
        </div>
        <div className="space-y-2">
          {coins.map((c) => {
            const active = selectedCoin === c.code;
            return (
              <button
                key={c.code}
                onClick={() => onSelectCoin && onSelectCoin(c.code)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all border ${
                  active
                    ? 'bg-blue-600/20 text-white border-blue-500/60 shadow-sm'
                    : 'bg-slate-800/40 text-slate-400 border-slate-800 hover:bg-slate-800 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <CoinLogo coin={c.code} size={24} className="shrink-0" />
                  <div className="text-left">
                    <div className="font-bold leading-tight">{c.pair}</div>
                    <div className="text-[10px] text-slate-400 font-normal">{c.name}</div>
                  </div>
                </div>
                {active && (
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Info Ringkas Model */}
      <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-3 text-[11px] text-slate-400 space-y-1.5">
        <div className="text-slate-300 font-semibold flex items-center gap-1.5 mb-1">
          <Layers size={12} className="text-indigo-400" /> Algoritma Prediksi
        </div>
        <div>
          <span className="text-blue-400 font-semibold">1 Hari:</span> LSTM
        </div>
        <div>
          <span className="text-indigo-400 font-semibold">3 Hari:</span> Hybrid LSTM + XGBoost
        </div>
        <div>
          <span className="text-purple-400 font-semibold">7 Hari:</span> Hybrid TCN + XGBoost
        </div>
      </div>

      <div className="text-[11px] text-slate-600 px-2 mt-auto pt-4">
        &copy; 2025 Sapar Hidayat
      </div>
    </div>
  );
};

export default Sidebar;
