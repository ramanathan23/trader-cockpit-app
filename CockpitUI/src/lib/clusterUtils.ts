import type { ScoredSymbol } from '@/domain/dashboard';

export const W  = 900;
export const H  = 540;
export const PAD = { top: 32, right: 28, bottom: 52, left: 56 } as const;
export const PW  = W - PAD.left - PAD.right;
export const PH  = H - PAD.top  - PAD.bottom;
export const QUAD_TOTAL   = 65;
export const QUAD_COMFORT = 65;

export interface ViewBounds { x0: number; x1: number; y0: number; y1: number; }

export function dotColor(row: ScoredSymbol): string {
  if (row.weekly_bias === 'BULLISH') return 'rgb(var(--bull))';
  if (row.weekly_bias === 'BEARISH') return 'rgb(var(--bear))';
  return 'rgb(var(--amber))';
}

export function dotRadius(totalScore: number): number {
  return Math.min(14, Math.max(4, 4 + (totalScore / 100) * 10));
}

export function axisTicks(min: number, max: number): number[] {
  const range = max - min;
  const step  = range <= 15 ? 2 : range <= 30 ? 5 : range <= 60 ? 10 : 25;
  const first = Math.ceil(min / step) * step;
  const ticks: number[] = [];
  for (let v = first; v <= max + 0.001; v += step) ticks.push(Math.round(v));
  return ticks;
}

export function mkToX(bounds: ViewBounds) {
  return (v: number) => PAD.left + ((v - bounds.x0) / (bounds.x1 - bounds.x0)) * PW;
}

export function mkToY(bounds: ViewBounds) {
  return (v: number) => PAD.top + (1 - (v - bounds.y0) / (bounds.y1 - bounds.y0)) * PH;
}
