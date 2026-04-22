export type Timeframe = '1m' | '3m' | '5m' | '15m' | '1h' | '1d' | '1w' | '1mo';

export const INTRADAY_TFS: Timeframe[] = ['1m', '3m', '5m', '15m', '1h'];
export const DAILY_TFS: Timeframe[] = ['1d', '1w', '1mo'];

export interface ChartBar {
  time: string | number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ProfileRow {
  price: number;
  vol: number;
  pct: number;
}

// NSE session: 375 min/day × 90 trading days
const INTRADAY_BARS: Record<string, { tfMins: number; bars: number }> = {
  '1m':  { tfMins: 1,  bars: 33750 },  // 90d × 375
  '3m':  { tfMins: 3,  bars: 11250 },  // 90d × 125
  '5m':  { tfMins: 5,  bars: 6750  },  // 90d × 75
  '15m': { tfMins: 15, bars: 2250  },  // 90d × 25
  '1h':  { tfMins: 60, bars: 630   },  // 90d × 7
};

export function tfToIntradayParams(tf: Timeframe): { tfMins: number; bars: number } {
  return INTRADAY_BARS[tf] ?? { tfMins: 1, bars: 33750 };
}

const DAILY_TF_DAYS: Record<string, number> = {
  '1d':  1825,
  '1w':  1825,
  '1mo': 1825,
};

export function buildChartUrl(symbol: string, tf: Timeframe): string {
  const enc = encodeURIComponent(symbol);
  if (DAILY_TFS.includes(tf)) {
    return `/api/v1/chart/${enc}/daily?days=${DAILY_TF_DAYS[tf] ?? 1825}`;
  }
  const { tfMins, bars } = tfToIntradayParams(tf);
  return `/api/v1/chart/${enc}/intraday?tf=${tfMins}&bars=${bars}`;
}

export function tfEMAPeriods(tf: Timeframe): { fast: number; slow: number; fastLabel: string; slowLabel: string } {
  switch (tf) {
    case '1m':
    case '3m':
    case '5m':  return { fast: 9,  slow: 21,  fastLabel: 'EMA9',   slowLabel: 'EMA21'  };
    case '15m':
    case '1h':  return { fast: 20, slow: 50,  fastLabel: 'EMA20',  slowLabel: 'EMA50'  };
    case '1d':  return { fast: 50, slow: 200, fastLabel: 'EMA50',  slowLabel: 'EMA200' };
    case '1w':  return { fast: 9,  slow: 21,  fastLabel: 'EMA9',   slowLabel: 'EMA21'  };
    case '1mo': return { fast: 6,  slow: 12,  fastLabel: 'EMA6',   slowLabel: 'EMA12'  };
    default:    return { fast: 50, slow: 200, fastLabel: 'EMA50',  slowLabel: 'EMA200' };
  }
}

export function fmtBarTime(time: string | number, isIntraday: boolean): string {
  if (isIntraday && typeof time === 'number') {
    const d = new Date(time * 1000);
    return d.toLocaleString('en-IN', {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
      hour12: false, timeZone: 'Asia/Kolkata',
    });
  }
  return String(time);
}

export function fmtVol(v: number): string {
  if (v >= 1e7) return `${(v / 1e7).toFixed(1)}Cr`;
  if (v >= 1e5) return `${(v / 1e5).toFixed(1)}L`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return String(v);
}

export function computeEMA(bars: ChartBar[], period: number): { time: string | number; value: number }[] {
  if (bars.length < period) return [];
  const k = 2 / (period + 1);
  const seed = bars.slice(0, period).reduce((s, b) => s + b.close, 0) / period;
  const result: { time: string | number; value: number }[] = [];
  let ema = seed;
  for (let i = period - 1; i < bars.length; i++) {
    if (i > period - 1) ema = bars[i].close * k + ema * (1 - k);
    result.push({ time: bars[i].time, value: ema });
  }
  return result;
}

export function resampleWeekly(bars: ChartBar[]): ChartBar[] {
  if (bars.length === 0) return [];
  const groups = new Map<string, ChartBar[]>();
  for (const bar of bars) {
    const d = new Date((bar.time as string) + 'T00:00:00Z');
    const day = d.getUTCDay();
    const shift = day === 0 ? -6 : 1 - day;
    const monday = new Date(d);
    monday.setUTCDate(d.getUTCDate() + shift);
    const key = monday.toISOString().slice(0, 10);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(bar);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, g]) => ({
      time: key,
      open: g[0].open,
      high: Math.max(...g.map(b => b.high)),
      low:  Math.min(...g.map(b => b.low)),
      close: g[g.length - 1].close,
      volume: g.reduce((s, b) => s + b.volume, 0),
    }));
}

export function resampleMonthly(bars: ChartBar[]): ChartBar[] {
  if (bars.length === 0) return [];
  const groups = new Map<string, ChartBar[]>();
  for (const bar of bars) {
    const key = (bar.time as string).slice(0, 7);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(bar);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, g]) => ({
      time: key + '-01',
      open: g[0].open,
      high: Math.max(...g.map(b => b.high)),
      low:  Math.min(...g.map(b => b.low)),
      close: g[g.length - 1].close,
      volume: g.reduce((s, b) => s + b.volume, 0),
    }));
}

export function buildVolumeProfile(bars: ChartBar[], buckets = 30): ProfileRow[] {
  if (bars.length === 0) return [];
  const lo = Math.min(...bars.map(b => b.low));
  const hi = Math.max(...bars.map(b => b.high));
  if (hi === lo) return [];
  const step = (hi - lo) / buckets;
  const profile = new Array<number>(buckets).fill(0);
  for (const b of bars) {
    const bLo = Math.max(0, Math.floor((b.low  - lo) / step));
    const bHi = Math.min(buckets - 1, Math.floor((b.high - lo) / step));
    const spread = bHi - bLo + 1;
    for (let i = bLo; i <= bHi; i++) profile[i] += b.volume / spread;
  }
  const maxVol = Math.max(...profile);
  return profile.map((vol, i) => ({
    price: lo + (i + 0.5) * step,
    vol,
    pct: maxVol > 0 ? vol / maxVol : 0,
  }));
}
