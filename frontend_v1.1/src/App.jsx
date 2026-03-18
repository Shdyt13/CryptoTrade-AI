import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import PriceTicker from './components/PriceTicker';
import PredictionCard from './components/PredictionCard';
import Analytics from './components/Analytics'; // Import halaman baru
import { ShieldCheck } from 'lucide-react';

// Halaman Dashboard (Isi lama dipindahkan ke sini)
const Dashboard = () => (
  <>
    {/* Header Mobile / Desktop */}
    <header className="mb-8 flex justify-between items-end border-b border-slate-800 pb-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2 md:hidden">ETH Predictor</h1>
        <h2 className="text-2xl font-bold text-white hidden md:block">Market Overview</h2>
        <p className="text-slate-400 text-sm">Real-time AI Forecasting Dashboard.</p>
      </div>
      <div className="flex items-center gap-2 text-green-400 text-xs bg-green-900/20 px-3 py-1 rounded-full border border-green-900/50">
        <ShieldCheck size={14} /> System Operational
      </div>
    </header>

    <PriceTicker />

    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <PredictionCard 
        title="Short Term (15m)" 
        timeframe="15m" 
        description="High-frequency prediction using XGBoost." 
      />
      <PredictionCard 
        title="Mid Term (1h)" 
        timeframe="1h" 
        description="Deep Learning (LSTM) 24h patterns." 
      />
      <PredictionCard 
        title="Weekly Forecast" 
        timeframe="1w" 
        description="Trend analysis using Facebook Prophet." 
      />
    </div>
  </>
);

function App() {
  return (
    <Router>
      <div className="flex min-h-screen bg-[#0f172a] text-slate-200 font-sans">
        
        {/* SIDEBAR (Hanya muncul di layar lebar) */}
        <Sidebar />

        {/* KONTEN UTAMA */}
        <div className="flex-1 md:ml-64 p-4 md:p-8 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </div>

      </div>
    </Router>
  );
}

export default App;