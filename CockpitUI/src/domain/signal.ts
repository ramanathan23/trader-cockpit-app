import type { InstrumentMetrics } from './instrument_metrics';

export type SignalType =
  | 'RANGE_BREAKOUT' | 'RANGE_BREAKDOWN'
  | 'CAM_H3_REVERSAL' | 'CAM_H4_BREAKOUT' | 'CAM_H4_REVERSAL'
  | 'CAM_L3_REVERSAL' | 'CAM_L4_BREAKDOWN' | 'CAM_L4_REVERSAL';

export type SignalCategory = 'ALL' | 'BREAK' | 'CAM';

export type Direction = 'BULLISH' | 'BEARISH' | 'NEUTRAL';

export interface Signal {
  id: string;
  symbol: string;
  signal_type: SignalType;
  direction?: Direction;
  price?: number;
  volume_ratio?: number;
  score?: number;
  timestamp: string;
  message?: string;
  bias_15m?: Direction;
  bias_1h?: Direction;
  entry_low?: number;
  entry_high?: number;
  stop?: number;
  target_1?: number;
  trail_stop?: number;
  watchlist_conflict?: boolean;
  _count: number;
  _dedupKey?: string;
  _fromCatchup?: boolean;
  _catchup?: boolean;
}

export const CATEGORY_TYPES: Record<Exclude<SignalCategory, 'ALL'>, SignalType[]> = {
  BREAK: ['RANGE_BREAKOUT', 'RANGE_BREAKDOWN'],
  CAM: [
    'CAM_H4_BREAKOUT', 'CAM_L4_BREAKDOWN',
    'CAM_H4_REVERSAL', 'CAM_H3_REVERSAL',
    'CAM_L4_REVERSAL', 'CAM_L3_REVERSAL',
  ],
};

interface SignalMeta {
  color: string;
  tint: string;
  short: string;
  desc: string;
}

const META: Record<SignalType, SignalMeta> = {
  RANGE_BREAKOUT:  { color: '#1ad48d', tint: 'rgba(26,212,141,0.05)',  short: 'RNG+',   desc: 'Rectangle consolidation broke upward on volume.' },
  RANGE_BREAKDOWN: { color: '#f75068', tint: 'rgba(247,80,104,0.05)',  short: 'RNG-',   desc: 'Rectangle consolidation broke downward on volume.' },
  CAM_H4_BREAKOUT: { color: '#b490ff', tint: 'rgba(180,144,255,0.05)', short: 'CAM H4+', desc: 'Closed above Camarilla H4 on volume (narrow pivot range).' },
  CAM_L4_BREAKDOWN:{ color: '#b490ff', tint: 'rgba(180,144,255,0.05)', short: 'CAM L4-', desc: 'Closed below Camarilla L4 on volume (narrow pivot range).' },
  CAM_H4_REVERSAL: { color: '#9b72f7', tint: 'rgba(155,114,247,0.05)', short: 'CAM H4↓', desc: 'Bearish pin bar rejection at Camarilla H4 (wide pivot range).' },
  CAM_H3_REVERSAL: { color: '#9b72f7', tint: 'rgba(155,114,247,0.05)', short: 'CAM H3↓', desc: 'Bearish pin bar rejection at Camarilla H3 (wide pivot range).' },
  CAM_L4_REVERSAL: { color: '#9b72f7', tint: 'rgba(155,114,247,0.05)', short: 'CAM L4↑', desc: 'Bullish pin bar bounce from Camarilla L4 (wide pivot range).' },
  CAM_L3_REVERSAL: { color: '#9b72f7', tint: 'rgba(155,114,247,0.05)', short: 'CAM L3↑', desc: 'Bullish pin bar bounce from Camarilla L3 (wide pivot range).' },
};

export function signalColor(type: SignalType): string {
  return META[type]?.color ?? '#30363d';
}

export function signalTint(type: SignalType): string {
  return META[type]?.tint ?? 'transparent';
}

export function signalShort(type: SignalType): string {
  return META[type]?.short ?? type;
}

export function signalDesc(type: SignalType): string {
  return META[type]?.desc ?? '';
}

export function dirColor(dir?: Direction): string {
  return dir === 'BULLISH' ? '#0dbd7d' : dir === 'BEARISH' ? '#f23d55' : '#5a7796';
}

export function advColor(cr: number): string {
  if (cr >= 500) return '#0dbd7d';
  if (cr >= 100) return '#e8933a';
  if (cr >= 25) return '#c5d8f0';
  return '#5a7796';
}

export function pctColor(value: number, reference: number): string {
  if (!reference) return '#5a7796';
  const p = (value - reference) / reference;
  return p > 0 ? '#0dbd7d' : p < 0 ? '#f23d55' : '#5a7796';
}

export function filterSignals(
  signals: Signal[],
  category: SignalCategory,
  minAdvCr: number,
  metricsCache: Record<string, InstrumentMetrics | null>,
  subType?: SignalType | null,
  fnoOnly?: boolean,
): Signal[] {
  return signals.filter(signal => {
    if (category !== 'ALL') {
      const allowed = CATEGORY_TYPES[category as Exclude<SignalCategory, 'ALL'>] ?? [];
      if (!allowed.includes(signal.signal_type)) return false;
    }

    if (subType && signal.signal_type !== subType) return false;
    if (fnoOnly && !metricsCache[signal.symbol]?.is_fno) return false;

    if (minAdvCr > 0) {
      const metrics = metricsCache[signal.symbol];
      if (metrics && (metrics.adv_20_cr ?? 0) < minAdvCr) return false;
    }

    return true;
  });
}
