// Signal domain — types, constants, and pure helper functions.
// Single Responsibility: all signal-related type definitions live here.

import type { InstrumentMetrics } from './instrument_metrics';

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

// ── Signal metadata (single source of truth per type) ────────────────────────

interface SignalMeta {
  color: string;
  tint:  string;
  short: string;
  desc:  string;
}

const META: Record<SignalType, SignalMeta> = {
  OPEN_DRIVE_ENTRY:    { color: '#0dbd7d', tint: 'rgba(13,189,125,0.06)',  short: 'DRIVE',    desc: 'Strong open drive — ride the momentum' },
  SPIKE_BREAKOUT:      { color: '#e8933a', tint: 'rgba(232,147,58,0.06)',  short: 'SPIKE',    desc: 'Volume shock breakout — watch for follow-through' },
  ABSORPTION:          { color: '#38b6ff', tint: 'rgba(56,182,255,0.06)',  short: 'ABS',      desc: 'Big vol, flat price — supply/demand absorbing' },
  EXHAUSTION_REVERSAL: { color: '#9b72f7', tint: 'rgba(155,114,247,0.06)', short: 'EXHAUST',  desc: 'Downtrend climax held — bounce reversal setup' },
  TRAIL_UPDATE:        { color: '#5a7796', tint: 'transparent',            short: 'TRAIL',    desc: 'Trailing stop moved up' },
  DRIVE_FAILED:        { color: '#f23d55', tint: 'rgba(242,61,85,0.06)',   short: 'FAILED',   desc: 'Drive failed — price back through open' },
  EXIT:                { color: '#f23d55', tint: 'rgba(242,61,85,0.06)',   short: 'EXIT',     desc: 'Position exited' },
  FADE_ALERT:          { color: '#d4a63a', tint: 'rgba(212,166,58,0.06)',  short: 'FADE',     desc: 'Big move, no volume — likely to fade/reverse' },
  ORB_BREAKOUT:        { color: '#0dbd7d', tint: 'rgba(13,189,125,0.05)', short: 'ORB↑',     desc: 'Closed above opening range high on volume' },
  ORB_BREAKDOWN:       { color: '#f23d55', tint: 'rgba(242,61,85,0.05)',  short: 'ORB↓',     desc: 'Closed below opening range low on volume' },
  RANGE_BREAKOUT:      { color: '#1ad48d', tint: 'rgba(26,212,141,0.05)', short: 'RNG↑',     desc: '5-candle consolidation broken upward on volume' },
  RANGE_BREAKDOWN:     { color: '#f75068', tint: 'rgba(247,80,104,0.05)', short: 'RNG↓',     desc: '5-candle consolidation broken downward on volume' },
  WEEK52_BREAKOUT:     { color: '#0dbd7d', tint: 'rgba(13,189,125,0.08)', short: '52W↑',     desc: '52-week high breakout on 2× volume' },
  WEEK52_BREAKDOWN:    { color: '#f23d55', tint: 'rgba(242,61,85,0.08)',  short: '52W↓',     desc: '52-week low breakdown on 2× volume' },
  PDH_BREAKOUT:        { color: '#25d692', tint: 'rgba(37,214,146,0.05)', short: 'PDH↑',     desc: 'Closed above previous day high on volume' },
  PDL_BREAKDOWN:       { color: '#f23d55', tint: 'rgba(242,61,85,0.05)',  short: 'PDL↓',     desc: 'Closed below previous day low on volume' },
  VWAP_BREAKOUT:       { color: '#38b6ff', tint: 'rgba(56,182,255,0.05)', short: 'VWAP↑',    desc: 'Price crossed above VWAP on volume — intraday bull' },
  VWAP_BREAKDOWN:      { color: '#e06cff', tint: 'rgba(224,108,255,0.05)',short: 'VWAP↓',    desc: 'Price crossed below VWAP on volume — intraday bear' },
  CAM_H3_REVERSAL:     { color: '#9b72f7', tint: 'rgba(155,114,247,0.05)',short: 'CAM H3',   desc: 'Rejected at Camarilla H3 — fade short setup' },
  CAM_H4_BREAKOUT:     { color: '#b490ff', tint: 'rgba(180,144,255,0.05)',short: 'CAM H4↑',  desc: 'Broke above Camarilla H4 — momentum long' },
  CAM_L3_REVERSAL:     { color: '#9b72f7', tint: 'rgba(155,114,247,0.05)',short: 'CAM L3',   desc: 'Bounced off Camarilla L3 — fade long setup' },
  CAM_L4_BREAKDOWN:    { color: '#b490ff', tint: 'rgba(180,144,255,0.05)',short: 'CAM L4↓',  desc: 'Broke below Camarilla L4 — momentum short' },
};

// ── Pure helper functions ────────────────────────────────────────────────────

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
  subType?: SignalType | null,
  fnoOnly?: boolean,
): Signal[] {
  return signals
    .filter(s => {
      if (category !== 'ALL') {
        const allowed = CATEGORY_TYPES[category as Exclude<SignalCategory, 'ALL'>] ?? [];
        if (!allowed.includes(s.signal_type)) return false;
      }
      if (subType && s.signal_type !== subType) return false;
      if (fnoOnly && !metricsCache[s.symbol]?.is_fno) return false;
      if (minAdvCr > 0) {
        const m = metricsCache[s.symbol];
        if (m && (m.adv_20_cr ?? 0) < minAdvCr) return false;
      }
      return true;
    });
}
