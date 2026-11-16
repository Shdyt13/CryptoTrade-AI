import { useEffect, useState } from 'react';

const resolveApiUrl = () => {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return 'http://localhost:8000';
};

const resolveWsUrl = () => {
  const envWs = import.meta.env.VITE_WS_URL;
  if (envWs) {
    const trimmed = envWs.replace(/\/+$/, '');
    return trimmed.endsWith('/ws') ? trimmed : `${trimmed}/ws`;
  }
  if (typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${window.location.hostname}:8000/ws`;
  }
  return 'ws://localhost:8000/ws';
};

export const API_URL = resolveApiUrl();
export const WS_URL = resolveWsUrl();

// Fallback kalkulasi rentang keputusan Buy/Hold/Sell & Auto Buy/Sell di sisi klien
export const computeClientDecision = (currentPrice, predictedPrice, changePercent, horizonDays = 1) => {
  const curr = Number(currentPrice || 0);
  const pred = Number(predictedPrice || curr);
  let pct = typeof changePercent === 'number' && !isNaN(changePercent) ? changePercent : 0;
  if (!pct && curr > 0 && pred > 0) {
    pct = ((pred - curr) / curr) * 100;
  }
  const scale = Math.max(Math.sqrt(Math.max(horizonDays, 1)), 1);
  const score = Math.max(-4.0, Math.min(4.0, pct / scale));

  const logitBuy = 0.42 * score;
  const logitSell = -0.42 * score;
  const logitHold = 0.35 - 0.22 * Math.abs(score);

  const maxLogit = Math.max(logitBuy, logitSell, logitHold);
  const expBuy = Math.exp(logitBuy - maxLogit);
  const expSell = Math.exp(logitSell - maxLogit);
  const expHold = Math.exp(logitHold - maxLogit);
  const sum = expBuy + expSell + expHold;

  let buyScore = Math.max(5, Math.round((expBuy / sum) * 100));
  let sellScore = Math.max(5, Math.round((expSell / sum) * 100));
  let holdScore = Math.max(5, 100 - buyScore - sellScore);

  const diff = 100 - (buyScore + sellScore + holdScore);
  if (diff !== 0) {
    if (score > 0.3) buyScore += diff;
    else if (score < -0.3) sellScore += diff;
    else holdScore += diff;
  }

  let decision = 'HOLD';
  if (buyScore >= sellScore && buyScore >= holdScore) decision = 'BUY';
  else if (sellScore >= buyScore && sellScore >= holdScore) decision = 'SELL';

  const volPct = Math.max(0.015, Math.min(0.08, 0.022 * Math.sqrt(Math.max(horizonDays, 1))));
  let autoBuy = curr * (1 - 0.55 * volPct);
  let autoSell = Math.max(pred, curr * (1 + 0.75 * volPct));
  let stopLoss = autoBuy * (1 - 0.75 * volPct);

  if (decision === 'SELL') {
    autoBuy = Math.min(pred, curr * (1 - 0.85 * volPct));
    autoSell = Math.max(curr * (1 - 0.1 * volPct), pred * (1 + 0.45 * volPct));
    stopLoss = autoBuy * (1 - 0.7 * volPct);
  } else if (decision === 'HOLD') {
    autoBuy = Math.min(curr, pred) * (1 - 0.65 * volPct);
    autoSell = Math.max(curr, pred) * (1 + 0.65 * volPct);
    stopLoss = autoBuy * (1 - 0.65 * volPct);
  }

  return {
    decision,
    buy_score: buyScore,
    hold_score: holdScore,
    sell_score: sellScore,
    auto_buy_price: Math.round(autoBuy),
    auto_sell_price: Math.round(autoSell),
    stop_loss_price: Math.round(stopLoss),
  };
};

// Shared WebSocket Manager
let sharedSocket = null;
let subscribers = new Set();
let latestMarketData = null;
let reconnectTimer = null;

const notifySubscribers = () => {
  for (const callback of subscribers) {
    try {
      callback(latestMarketData);
    } catch (err) {
      console.error('Error notifying subscriber:', err);
    }
  }
};

const connectWebSocket = () => {
  if (typeof window === 'undefined') return;
  if (
    sharedSocket &&
    (sharedSocket.readyState === WebSocket.OPEN ||
      sharedSocket.readyState === WebSocket.CONNECTING)
  ) {
    return;
  }

  try {
    const socket = new WebSocket(WS_URL);
    sharedSocket = socket;

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        latestMarketData = parsed;
        notifySubscribers();
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    socket.onerror = (err) => {
      console.warn('WebSocket connection error:', err);
    };

    socket.onclose = () => {
      sharedSocket = null;
      if (subscribers.size > 0 && !reconnectTimer) {
        reconnectTimer = setTimeout(() => {
          reconnectTimer = null;
          connectWebSocket();
        }, 3000);
      }
    };
  } catch (err) {
    console.error('Failed to initialize WebSocket:', err);
    if (subscribers.size > 0 && !reconnectTimer) {
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connectWebSocket();
      }, 3000);
    }
  }
};

export const useMarketData = () => {
  const [marketData, setMarketData] = useState(latestMarketData);
  const [loading, setLoading] = useState(!latestMarketData);

  useEffect(() => {
    const handler = (data) => {
      setMarketData(data);
      setLoading(false);
    };

    subscribers.add(handler);
    if (latestMarketData) {
      setMarketData(latestMarketData);
      setLoading(false);
    }

    connectWebSocket();

    return () => {
      subscribers.delete(handler);
      if (subscribers.size === 0 && sharedSocket) {
        setTimeout(() => {
          if (subscribers.size === 0 && sharedSocket) {
            sharedSocket.close();
            sharedSocket = null;
          }
        }, 5000);
      }
    };
  }, []);

  return { marketData, loading };
};

export const useLatestPrice = (coin = 'ETH') => {
  const { marketData, loading } = useMarketData();
  const coinKey = (coin || 'ETH').toUpperCase();
  const coinPrice =
    marketData?.coins?.[coinKey]?.price ||
    (coinKey === 'ETH' ? marketData?.price : null) ||
    null;
  return { priceData: coinPrice, loading };
};

export const usePrediction = (timeframe, coin = 'ETH') => {
  const { marketData } = useMarketData();
  const coinKey = (coin || 'ETH').toUpperCase();
  const wsValidation = marketData?.coins?.[coinKey]?.validation || null;

  if (wsValidation && wsValidation.valid === false) {
    return {
      prediction_blocked: true,
      reason: wsValidation.reason,
      data_validation: wsValidation,
    };
  }

  const rawPred =
    marketData?.coins?.[coinKey]?.predictions?.[timeframe] ||
    (coinKey === 'ETH' ? marketData?.predictions?.[timeframe] : null) ||
    null;

  if (!rawPred) return null;

  const horizonDays = timeframe === '7d' ? 7 : timeframe === '3d' ? 3 : 1;
  const fallback = computeClientDecision(
    Number(rawPred.current_price_at_prediction || rawPred.last_close || 0),
    Number(rawPred.predicted_price || 0),
    rawPred.change_percent,
    horizonDays
  );

  const hasScores =
    (Number(rawPred.buy_score) || 0) +
      (Number(rawPred.hold_score) || 0) +
      (Number(rawPred.sell_score) || 0) >
    0;

  return {
    ...fallback,
    ...rawPred,
    buy_score: hasScores ? rawPred.buy_score : fallback.buy_score,
    hold_score: hasScores ? rawPred.hold_score : fallback.hold_score,
    sell_score: hasScores ? rawPred.sell_score : fallback.sell_score,
    decision: hasScores && rawPred.decision ? rawPred.decision : fallback.decision,
    auto_buy_price: rawPred.auto_buy_price ?? fallback.auto_buy_price,
    auto_sell_price: rawPred.auto_sell_price ?? fallback.auto_sell_price,
    stop_loss_price: rawPred.stop_loss_price ?? fallback.stop_loss_price,
    data_validation: rawPred.data_validation || wsValidation,
  };
};

export const useDailyCandles = (coin = 'ETH', limit = 45) => {
  const { marketData } = useMarketData();
  const coinKey = (coin || 'ETH').toUpperCase();
  const [bundle, setBundle] = useState(null);
  const [loading, setLoading] = useState(true);

  const wsCandles = marketData?.coins?.[coinKey]?.candles || null;
  const wsValidation = marketData?.coins?.[coinKey]?.validation || null;

  useEffect(() => {
    let active = true;
    setLoading(true);

    const fetchCandles = async () => {
      try {
        const res = await fetch(`${API_URL}/api/candles/${coinKey}?limit=${limit}`);
        if (!res.ok) throw new Error(`Status ${res.status}`);
        const data = await res.json();
        if (active) setBundle(data);
      } catch (err) {
        console.error('Error fetching daily candles:', err);
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchCandles();
    const interval = setInterval(fetchCandles, 60000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [coinKey, limit]);

  const candles =
    Array.isArray(wsCandles) && wsCandles.length > 0
      ? wsCandles.slice(-limit)
      : Array.isArray(bundle?.candles)
      ? bundle.candles.slice(-limit)
      : [];

  const validation = wsValidation || bundle?.validation || null;
  const requiredVariables = bundle?.required_variables || [
    'open',
    'high',
    'low',
    'close',
    'volume',
  ];

  return {
    candles,
    validation,
    requiredVariables,
    loading: loading && candles.length === 0,
  };
};

export const useEvaluationSummary = (coin = 'ETH') => {
  const { marketData } = useMarketData();
  const coinKey = (coin || 'ETH').toUpperCase();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  const wsSummary = marketData?.coins?.[coinKey]?.evaluation || null;

  useEffect(() => {
    let active = true;
    const fetchSummary = async () => {
      try {
        const res = await fetch(`${API_URL}/api/evaluation?coin=${coinKey}`);
        if (!res.ok) throw new Error(`Status ${res.status}`);
        const data = await res.json();
        if (active) setSummary(data);
      } catch (err) {
        console.error('Error fetching evaluation summary:', err);
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchSummary();
    const interval = setInterval(fetchSummary, 60000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [coinKey]);

  return { evaluationSummary: wsSummary || summary, loading: loading && !wsSummary };
};

export const usePredictionHistory = (
  timeframe = '1d',
  coin = 'ETH',
  onlyEvaluated = false,
  limit = 30
) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const coinKey = (coin || 'ETH').toUpperCase();

  useEffect(() => {
    let active = true;
    setLoading(true);

    const fetchHistory = async () => {
      try {
        const endpoint = onlyEvaluated
          ? `${API_URL}/api/evaluated/${timeframe}?coin=${coinKey}&limit=${limit}`
          : `${API_URL}/api/history/${timeframe}?coin=${coinKey}&limit=${limit}`;
        const response = await fetch(endpoint);
        if (!response.ok) throw new Error(`History request failed: ${response.status}`);
        const data = await response.json();
        if (active) {
          setHistory(Array.isArray(data) ? data : []);
        }
      } catch (error) {
        console.error('Error fetching prediction history:', error);
        if (active) setHistory([]);
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchHistory();
    const interval = setInterval(fetchHistory, 60000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [timeframe, coinKey, onlyEvaluated, limit]);

  return { history, loading };
};
