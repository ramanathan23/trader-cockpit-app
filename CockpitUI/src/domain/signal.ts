// Signal domain — types, constants, and pure helper functions.
// Single Responsibility: all signal-related type definitions live here.

export type SignalType =
  | 'OPEN_DRIVE_ENTRY' | 'DRIVE_FAILED' | 'EXIT' | 'TRAIL_UPDATE'
  | 'SPIKE_BREAKOUT'
  | 'ABSORPTION'
  | 'EXHAUSTION_REVERSAL'
  | 'FADE_ALERT'
  | 'ORB_BREAKOUT'  | 'ORB_BREAKDOWN'
  | 'RANGE_BREAKOUT' | 'RANGE_BREAKDOWN'
  | 'WEEK52_BREAKOUT' | 'WEEK52_BREAKDOWN'
  | 'PDH_BREAKOUT' | 'PDL_BREAKDOWN'
  | 'VWAP_BREAKOUT' | 'VWAP_BREAKDOWN'
  | 'CAM_H3_REVERSAL' | 'CAM_H4_BREAKOUT' | 'CAM_L3_REVERSAL' | 'CAM_L4_BREAKDOWN';

export type SignalCategory =
  | 'ALL' | 'DRIVE' | 'SPIKE' | 'ABS' | 'EXHAUST' | 'FADE' | 'BREAK' | 'VWAP' | 'CAM';

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
  // Internal UI fields
  _count: number;
  _dedupKey?: string;
  _fromCatchup?: boolean;
  _catchup?: boolean;
}

export interface InstrumentMetrics {
  symbol: string;
  day_high?: number;
  day_low?: number;
  day_open?: number;
  day_chg_pct?: number;
  week52_high?: number;
  week52_low?: number;
  prev_day_high?: number;
  prev_day_low?: number;
  prev_day_close?: number;
  prev_week_high?: number;
  prev_week_low?: number;
  prev_month_high?: number;
  prev_month_low?: number;
  atr_14?: number;
  adv_20_cr?: number;
}

// ── Category mapping ─────────────────────────────────────────────────────────

export const CATEGORY_TYPES: Record<Exclude<SignalCategory, 'ALL'>, SignalType[]> = {
  DRIVE:   ['OPEN_DRIVE_ENTRY', 'DRIVE_FAILED', 'EXIT', 'TRAIL_UPDATE'],
  SPIKE:   ['SPIKE_BREAKOUT'],
  ABS:     ['ABSORPTION'],
  EXHAUST: ['EXHAUSTION_REVERSAL'],
  FADE:    ['FADE_ALERT'],
  BREAK:   ['ORB_BREAKOUT', 'ORB_BREAKDOWN', 'RANGE_BREAKOUT', 'RANGE_BREAKDOWN',
            'WEEK52_BREAKOUT', 'WEEK52_BREAKDOWN', 'PDH_BREAKOUT', 'PDL_BREAKDOWN'],
  VWAP:    ['VWAP_BREAKOUT', 'VWAP_BREAKDOWN'],
  CAM:     ['CAM_H3_REVERSAL', 'CAM_H4_BREAKOUT', 'CAM_L3_REVERSAL', 'CAM_L4_BREAKDOWN'],
};

// ── Color palette ────────────────────────────────────────────────────────────

const COLORS: Partial<Record<SignalType, string>> = {
  OPEN_DRIVE_ENTRY:    '#0dbd7d',
  SPIKE_BREAKOUT:      '#e8933a',
  ABSORPTION:          '#38b6ff',
  EXHAUSTION_REVERSAL: '#9b72f7',
  TRAIL_UPDATE:        '#5a7796',
  DRIVE_FAILED:        '#f23d55',
  EXIT:                '#f23d55',
  FADE_ALERT:          '#d4a63a',
  ORB_BREAKOUT:        '#0dbd7d',
  ORB_BREAKDOWN:       '#f23d55',
  RANGE_BREAKOUT:      '#1ad48d',
  RANGE_BREAKDOWN:     '#f75068',
  WEEK52_BREAKOUT:     '#0dbd7d',
  WEEK52_BREAKDOWN:    '#f23d55',
  PDH_BREAKOUT:        '#25d692',
  PDL_BREAKDOWN:       '#f23d55',
  VWAP_BREAKOUT:       '#38b6ff',
  VWAP_BREAKDOWN:      '#e06cff',
  CAM_H3_REVERSAL:     '#9b72f7',
  CAM_H4_BREAKOUT:     '#b490ff',
  CAM_L3_REVERSAL:     '#9b72f7',
  CAM_L4_BREAKDOWN:    '#b490ff',
};

const TINTS: Partial<Record<SignalType, string>> = {
  OPEN_DRIVE_ENTRY:    'rgba(13,189,125,0.06)',
  SPIKE_BREAKOUT:      'rgba(232,147,58,0.06)',
  ABSORPTION:          'rgba(56,182,255,0.06)',
  EXHAUSTION_REVERSAL: 'rgba(155,114,247,0.06)',
  DRIVE_FAILED:        'rgba(242,61,85,0.06)',
  EXIT:                'rgba(242,61,85,0.06)',
  FADE_ALERT:          'rgba(212,166,58,0.06)',
  ORB_BREAKOUT:        'rgba(13,189,125,0.05)',
  ORB_BREAKDOWN:       'rgba(242,61,85,0.05)',
  RANGE_BREAKOUT:      'rgba(26,212,141,0.05)',
  RANGE_BREAKDOWN:     'rgba(247,80,104,0.05)',
  WEEK52_BREAKOUT:     'rgba(13,189,125,0.08)',
  WEEK52_BREAKDOWN:    'rgba(242,61,85,0.08)',
  PDH_BREAKOUT:        'rgba(37,214,146,0.05)',
  PDL_BREAKDOWN:       'rgba(242,61,85,0.05)',
  VWAP_BREAKOUT:       'rgba(56,182,255,0.05)',
  VWAP_BREAKDOWN:      'rgba(224,108,255,0.05)',
  CAM_H3_REVERSAL:     'rgba(155,114,247,0.05)',
  CAM_H4_BREAKOUT:     'rgba(180,144,255,0.05)',
  CAM_L3_REVERSAL:     'rgba(155,114,247,0.05)',
  CAM_L4_BREAKDOWN:    'rgba(180,144,255,0.05)',
};

const SHORT: Partial<Record<SignalType, string>> = {
  OPEN_DRIVE_ENTRY:    'DRIVE',
  SPIKE_BREAKOUT:      'SPIKE',
  ABSORPTION:          'ABS',
  EXHAUSTION_REVERSAL: 'EXHAUST',
  TRAIL_UPDATE:        'TRAIL',
  DRIVE_FAILED:        'FAILED',
  EXIT:                'EXIT',
  FADE_ALERT:          'FADE',
  ORB_BREAKOUT:        'ORB↑',
  ORB_BREAKDOWN:       'ORB↓',
  RANGE_BREAKOUT:      'RNG↑',
  RANGE_BREAKDOWN:     'RNG↓',
  WEEK52_BREAKOUT:     '52W↑',
  WEEK52_BREAKDOWN:    '52W↓',
  PDH_BREAKOUT:        'PDH↑',
  PDL_BREAKDOWN:       'PDL↓',
  VWAP_BREAKOUT:       'VWAP↑',
  VWAP_BREAKDOWN:      'VWAP↓',
  CAM_H3_REVERSAL:     'CAM H3',
  CAM_H4_BREAKOUT:     'CAM H4↑',
  CAM_L3_REVERSAL:     'CAM L3',
  CAM_L4_BREAKDOWN:    'CAM L4↓',
};

const DESC: Partial<Record<SignalType, string>> = {
  OPEN_DRIVE_ENTRY:    'Strong open drive — ride the momentum',
  SPIKE_BREAKOUT:      'Volume shock breakout — watch for follow-through',
  ABSORPTION:          'Big vol, flat price — supply/demand absorbing',
  EXHAUSTION_REVERSAL: 'Downtrend climax held — bounce reversal setup',
  TRAIL_UPDATE:        'Trailing stop moved up',
  DRIVE_FAILED:        'Drive failed — price back through open',
  EXIT:                'Position exited',
  FADE_ALERT:          'Big move, no volume — likely to fade/reverse',
  ORB_BREAKOUT:        'Closed above opening range high on volume',
  ORB_BREAKDOWN:       'Closed below opening range low on volume',
  RANGE_BREAKOUT:      '5-candle consolidation broken upward on volume',
  RANGE_BREAKDOWN:     '5-candle consolidation broken downward on volume',
  WEEK52_BREAKOUT:     '52-week high breakout on 2× volume',
  WEEK52_BREAKDOWN:    '52-week low breakdown on 2× volume',
  PDH_BREAKOUT:        'Closed above previous day high on volume',
  PDL_BREAKDOWN:       'Closed below previous day low on volume',
  VWAP_BREAKOUT:       'Price crossed above VWAP on volume — intraday bull',
  VWAP_BREAKDOWN:      'Price crossed below VWAP on volume — intraday bear',
  CAM_H3_REVERSAL:     'Rejected at Camarilla H3 — fade short setup',
  CAM_H4_BREAKOUT:     'Broke above Camarilla H4 — momentum long',
  CAM_L3_REVERSAL:     'Bounced off Camarilla L3 — fade long setup',
  CAM_L4_BREAKDOWN:    'Broke below Camarilla L4 — momentum short',
};

// ── Pure helper functions ────────────────────────────────────────────────────

export function signalColor(type: SignalType): string {
  return COLORS[type] ?? '#30363d';
}

export function signalTint(type: SignalType): string {
  return TINTS[type] ?? 'transparent';
}

export function signalShort(type: SignalType): string {
  return SHORT[type] ?? type;
}

export function signalDesc(type: SignalType): string {
  return DESC[type] ?? '';
}

export function dirColor(dir?: Direction): string {
  return dir === 'BULLISH' ? '#0dbd7d' : dir === 'BEARISH' ? '#f23d55' : '#5a7796';
}

export function advColor(cr: number): string {
  if (cr >= 500) return '#0dbd7d';
  if (cr >= 100) return '#e8933a';
  if (cr >= 25)  return '#c5d8f0';
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
): Signal[] {
  return signals
    .filter(s => {
      if (category !== 'ALL') {
        const allowed = CATEGORY_TYPES[category as Exclude<SignalCategory, 'ALL'>] ?? [];
        if (!allowed.includes(s.signal_type)) return false;
      }
      if (minAdvCr > 0) {
        const m = metricsCache[s.symbol];
        if (m && (m.adv_20_cr ?? 0) < minAdvCr) return false;
      }
      return true;
    });
}
