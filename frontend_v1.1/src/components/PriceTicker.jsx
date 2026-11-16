import React from 'react';
import { useLatestPrice } from '../hooks/useRealtimeData';
import { CandlestickChart, BarChart3, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { CoinLogo } from './CoinIcons';

const COIN_META = {
  ETH: {
    name: 'Ethereum',
    pair: 'ETH/IDR',
    badgeClass: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40',
  },
  SUI: {
    name: 'Sui Network',
    pair: 'SUI/IDR',
    badgeClass: 'bg-sky-500/20 text-sky-300 border-sky-500/40',
  },
};

const PriceTicker = ({ coin = 'ETH' }) => {
  const coinKey = (coin || 'ETH').toUpperCase();
  const meta = COIN_META[coinKey] || COIN_META.ETH;
  const { priceData, loading } = useLatestPrice(coinKey);

  if (loading) {
    return (
      <div className="animate-pulse h-24 bg-slate-800 rounded-2xl mb-6 border border-slate-700"></div>
    );
  }

  if (!priceData) {
    return (
      <div className="bg-slate-800 p-5 rounded-2xl border border-slate-700 shadow-lg mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3 text-slate-300 text-sm">
          <CoinLogo coin={coinKey} size={32} />
          <span>Live Market ({meta.pair} - Indodax)</span>
        </div>
        <div className="text-amber-400 text-xs font-medium">Menunggu data harga {coinKey}...</div>
      </div>
    );
  }

  const priceDisplay =
    typeof priceData?.price === 'number'
      ? priceData.price.toLocaleString('id-ID')
      : priceData?.price != null
      ? String(priceData.price)
      : '0';

  const highDisplay =
    typeof priceData?.high === 'number' ? priceData.high.toLocaleString('id-ID') : '-';
  const lowDisplay =
    typeof priceData?.low === 'number' ? priceData.low.toLocaleString('id-ID') : '-';

  const volumeValue = typeof priceData?.volume === 'number' ? priceData.volume : 0;
  const volumeDisplay =
    volumeValue >= 1_000_000_000
      ? `${(volumeValue / 1_000_000_000).toFixed(2)} Miliar`
      : `${(volumeValue / 1_000_000).toFixed(2)} Juta`;

  return (
    <div className="bg-slate-800 p-5 rounded-2xl border border-slate-700 shadow-lg flex flex-col md:flex-row justify-between md:items-center gap-4 mb-6">
      <div className="flex items-center gap-4">
        <CoinLogo coin={coinKey} size={46} className="shrink-0 drop-shadow-md" />
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span
              className={`px-2.5 py-0.5 text-xs font-bold rounded-full border flex items-center gap-1 ${meta.badgeClass}`}
            >
              {meta.pair}
            </span>
            <span className="text-slate-400 text-xs font-medium flex items-center gap-1">
              <CandlestickChart size={14} className="text-emerald-400" /> Spot Market Indodax — {meta.name}
            </span>
          </div>
          <div className="text-2xl md:text-3xl font-bold text-white tracking-tight font-mono">
            Rp {priceDisplay}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-6 md:text-right border-t md:border-t-0 border-slate-700/60 pt-3 md:pt-0">
        <div>
          <div className="text-xs text-slate-400 mb-0.5">Rentang Harian (24h High / Low)</div>
          <div className="text-xs font-mono flex items-center md:justify-end gap-2">
            <span className="text-emerald-400 inline-flex items-center gap-0.5">
              <ArrowUpRight size={13} /> Rp {highDisplay}
            </span>
            <span className="text-slate-600">|</span>
            <span className="text-rose-400 inline-flex items-center gap-0.5">
              <ArrowDownRight size={13} /> Rp {lowDisplay}
            </span>
          </div>
        </div>
        <div>
          <div className="text-xs text-slate-400 mb-0.5 flex items-center md:justify-end gap-1">
            <BarChart3 size={12} className="text-blue-400" /> Volume 24h
          </div>
          <div className="text-slate-200 font-mono text-sm font-semibold">IDR {volumeDisplay}</div>
        </div>
      </div>
    </div>
  );
};

export default PriceTicker;
