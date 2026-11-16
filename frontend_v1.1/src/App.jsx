import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import PriceTicker from './components/PriceTicker';
import PredictionCard from './components/PredictionCard';
import CandlestickChart from './components/CandlestickChart';
import Analytics from './components/Analytics';
import ErrorBoundary from './components/ErrorBoundary';
import { CoinLogo, TradingLogoIcon } from './components/CoinIcons';

function App() {
  const [selectedCoin, setSelectedCoin] = useState('ETH');

  return (
    <ErrorBoundary>
      <div className="flex min-h-screen bg-[#0f172a] text-slate-200 font-sans">
        {/* SIDEBAR */}
        <Sidebar selectedCoin={selectedCoin} onSelectCoin={setSelectedCoin} />

        {/* KONTEN UTAMA */}
        <main className="flex-1 md:ml-60 p-4 md:p-7 overflow-y-auto min-h-screen max-w-7xl mx-auto">
          {/* Header Bertema Trading dengan Logo Koin */}
          <header className="mb-6 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="md:hidden">
                <TradingLogoIcon size={34} />
              </div>
              <CoinLogo coin={selectedCoin} size={36} className="shrink-0 drop-shadow" />
              <div>
                <h1 className="text-lg md:text-2xl font-bold text-white flex items-center gap-2">
                  <span>
                    {selectedCoin === 'SUI'
                      ? 'Sui Network (SUI/IDR)'
                      : 'Ethereum (ETH/IDR)'}{' '}
                    — AI Trading Predictor
                  </span>
                </h1>
                <p className="text-slate-400 text-xs mt-0.5">
                  Prediksi Harga Close Harian (1, 3, 7 Hari), Rekomendasi Buy/Hold/Sell, Auto Buy/Sell &amp; Evaluasi Aktual.
                </p>
              </div>
            </div>

            {/* Pemilih Koin ETH / SUI dengan Logo Resmi */}
            <div className="flex items-center bg-slate-900 p-1.5 rounded-xl border border-slate-700 self-start sm:self-auto gap-1">
              {[
                { code: 'ETH', label: 'ETH/IDR' },
                { code: 'SUI', label: 'SUI/IDR' },
              ].map((item) => {
                const active = selectedCoin === item.code;
                return (
                  <button
                    key={item.code}
                    onClick={() => setSelectedCoin(item.code)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                      active
                        ? 'bg-blue-600 text-white shadow'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800'
                    }`}
                  >
                    <CoinLogo coin={item.code} size={18} />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </div>
          </header>

          {/* 1. Harga Pasar Saat Ini */}
          <PriceTicker coin={selectedCoin} />

          {/* 2. Kartu Prediksi 3 Horizon (1 Hari, 3 Hari, 7 Hari) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-8">
            <PredictionCard
              coin={selectedCoin}
              title="Prediksi 1 Hari (1d)"
              timeframe="1d"
              modelBadge="LSTM (Daily OHLCV)"
            />
            <PredictionCard
              coin={selectedCoin}
              title="Prediksi 3 Hari (3d)"
              timeframe="3d"
              modelBadge="Hybrid LSTM + XGBoost"
            />
            <PredictionCard
              coin={selectedCoin}
              title="Prediksi 7 Hari (7d)"
              timeframe="7d"
              modelBadge="Hybrid TCN + XGBoost"
            />
          </div>

          {/* 3. Grafik Candlestick & Level Strategi Auto Buy / Auto Sell */}
          <CandlestickChart coin={selectedCoin} />

          {/* 4. Grafik Aktual vs Prediksi & Tabel Selisih Kesalahan */}
          <Analytics coin={selectedCoin} />
        </main>
      </div>
    </ErrorBoundary>
  );
}

export default App;
