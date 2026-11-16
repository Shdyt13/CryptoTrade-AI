import React from 'react';

/**
 * Icon Logo Sistem Bertema Trading (Candlestick + Garis Tren Bullish)
 */
export const TradingLogoIcon = ({ size = 36, className = '' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 64 64"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
  >
    <defs>
      <linearGradient id="tradeBg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stopColor="#0f172a" />
        <stop offset="100%" stopColor="#1e293b" />
      </linearGradient>
      <linearGradient id="bullCandle" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#34d399" />
        <stop offset="100%" stopColor="#059669" />
      </linearGradient>
      <linearGradient id="bearCandle" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#fb7185" />
        <stop offset="100%" stopColor="#e11d48" />
      </linearGradient>
      <linearGradient id="trendLine" x1="8" y1="48" x2="56" y2="12" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stopColor="#38bdf8" />
        <stop offset="100%" stopColor="#10b981" />
      </linearGradient>
    </defs>
    <rect width="64" height="64" rx="16" fill="url(#tradeBg)" stroke="#3b82f6" strokeWidth="2" />
    {/* Candle 1 */}
    <line x1="16" y1="26" x2="16" y2="52" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" />
    <rect x="12" y="32" width="8" height="14" rx="2" fill="url(#bullCandle)" />
    {/* Candle 2 */}
    <line x1="31" y1="22" x2="31" y2="48" stroke="#f43f5e" strokeWidth="2.5" strokeLinecap="round" />
    <rect x="27" y="27" width="8" height="13" rx="2" fill="url(#bearCandle)" />
    {/* Candle 3 */}
    <line x1="46" y1="12" x2="46" y2="42" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" />
    <rect x="42" y="17" width="8" height="18" rx="2" fill="url(#bullCandle)" />
    {/* Trend Arrow */}
    <path
      d="M10 47 L25 36 L36 40 L54 14"
      stroke="url(#trendLine)"
      strokeWidth="3"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M46 14 H54 V22"
      stroke="#34d399"
      strokeWidth="3"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

/**
 * Icon Logo Resmi Ethereum (ETH)
 */
export const EthLogoIcon = ({ size = 24, className = '' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 64 64"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
  >
    <defs>
      <linearGradient id="ethBg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stopColor="#627EEA" />
        <stop offset="100%" stopColor="#3B5998" />
      </linearGradient>
    </defs>
    <circle cx="32" cy="32" r="30" fill="url(#ethBg)" stroke="#93c5fd" strokeWidth="1.5" strokeOpacity="0.4" />
    {/* Diamond Atas */}
    <polygon points="32,10 18,32.5 32,26.2" fill="#FFFFFF" fillOpacity="0.9" />
    <polygon points="32,10 46,32.5 32,26.2" fill="#FFFFFF" fillOpacity="0.65" />
    <polygon points="32,26.2 18,32.5 32,40.5" fill="#FFFFFF" fillOpacity="0.8" />
    <polygon points="32,26.2 46,32.5 32,40.5" fill="#FFFFFF" fillOpacity="0.5" />
    {/* Diamond Bawah */}
    <polygon points="32,43.2 18,35.2 32,54" fill="#FFFFFF" fillOpacity="0.9" />
    <polygon points="32,43.2 46,35.2 32,54" fill="#FFFFFF" fillOpacity="0.65" />
  </svg>
);

/**
 * Icon Logo Resmi Sui Network (SUI)
 */
export const SuiLogoIcon = ({ size = 24, className = '' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 64 64"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
  >
    <defs>
      <linearGradient id="suiBg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stopColor="#4DA2FF" />
        <stop offset="100%" stopColor="#0284C7" />
      </linearGradient>
    </defs>
    <circle cx="32" cy="32" r="30" fill="url(#suiBg)" stroke="#bae6fd" strokeWidth="1.5" strokeOpacity="0.4" />
    {/* Bentuk Tetesan Air & Gelombang S khas Sui */}
    <path
      d="M32 11C32 11 17 26.5 17 37.5C17 45.8 23.7 52.5 32 52.5C40.3 52.5 47 45.8 47 37.5C47 26.5 32 11 32 11Z"
      stroke="#FFFFFF"
      strokeWidth="4"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M23.5 34.5C26.5 31 31.5 31.5 34.5 35.5C37.5 39.5 41.5 39.5 44.5 36.5"
      stroke="#FFFFFF"
      strokeWidth="3.8"
      strokeLinecap="round"
    />
    <path
      d="M26 25.5C29 23.5 33 24 36 27.5"
      stroke="#FFFFFF"
      strokeWidth="3.2"
      strokeLinecap="round"
      strokeOpacity="0.85"
    />
  </svg>
);

/**
 * Komponen pemilih otomatis logo koin berdasarkan kode ('ETH' atau 'SUI')
 */
export const CoinLogo = ({ coin = 'ETH', size = 24, className = '' }) => {
  const code = (coin || 'ETH').toUpperCase();
  if (code === 'SUI') {
    return <SuiLogoIcon size={size} className={className} />;
  }
  return <EthLogoIcon size={size} className={className} />;
};
