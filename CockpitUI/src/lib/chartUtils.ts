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

export interface TPOLevel {
  price: number;
  periods: number[];
}

export const PERIOD_COLORS = [
  '#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#1abc9c',
  '#3498db', '#9b59b6', '#e91e63', '#00bcd4', '#8bc34a',
  '#ff5722', '#607d8b', '#795548',
];

/** Backend query params for each intraday timeframe */
export function tfToIntradayParams(tf: Timeframe): { tfMins: number; bars: number } {
  switch (tf) {
    case '1m':  return { tfMins: 1,  bars: 390 };
    case '3m':  return { tfMins: 3,  bars: 390 };
    case '5m':  return { tfMins: 5,  bars: 390 };
    case '15m': return { tfMins: 15, bars: 390 };
    case '1h':  return { tfMins: 60, bars: 200 };
    default:    return { tfMins: 1,  bars: 390 };
  }
}

export function buildChartUrl(symbol: string, tf: Timeframe): string {
  const enc = encodeURIComponent(symbol);
  if (DAILY_TFS.includes(tf)) {
    const days = tf === '1mo' ? 1825 : 730;
    return `/api/v1/chart/${enc}/daily?days=${days}`;
  }
  const { tfMins, bars } = tfToIntradayParams(tf);
  return `/api/v1/chart/${enc}/intraday?tf=${tfMins}&bars=${bars}`;
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
      low: Math.min(...g.map(b => b.low)),
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
      low: Math.min(...g.map(b => b.low)),
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

export function autoTickSize(price: number): number {
  if (price >= 5000) return 5;
  if (price >= 2000) return 2;
  if (price >= 1000) return 1;
  if (price >= 200)  return 0.5;
  return 0.25;
}

export function buildTPO(bars: ChartBar[], tickSize: number, periodMins = 30): TPOLevel[] {
  if (bars.length === 0 || typeof bars[0].time !== 'number') return [];
  const sessionStart = bars[0].time as number;
  const levelMap = new Map<number, Set<number>>();
  for (const bar of bars) {
    const periodIdx = Math.floor(((bar.time as number) - sessionStart) / (periodMins * 60));
    const loTick = Math.floor(bar.low  / tickSize);
    const hiTick = Math.ceil(bar.high / tickSize);
    for (let tick = loTick; tick <= hiTick; tick++) {
      if (!levelMap.has(tick)) levelMap.set(tick, new Set());
      levelMap.get(tick)!.add(periodIdx);
    }
  }
  return [...levelMap.entries()]
    .map(([tick, ps]) => ({
      price: tick * tickSize,
      periods: [...ps].sort((a, b) => a - b),
    }))
    .sort((a, b) => b.price - a.price);
}
