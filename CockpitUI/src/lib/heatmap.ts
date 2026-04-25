export interface HeatMapEntry {
  symbol: string;
  adv: number;
  chgPct: number | null;
  price?: number | null;
  score?: number;
  stage?: string;
  signal?: string;
}

export function heatChgColor(pct: number | null): string {
  if (pct == null) return 'rgb(var(--lift))';
  if (pct > 5) return '#00a972';
  if (pct > 3) return '#078d67';
  if (pct > 1.5) return '#16775f';
  if (pct > 0.5) return '#2f665a';
  if (pct > -0.5) return '#879295';
  if (pct > -1.5) return '#8b5d66';
  if (pct > -3) return '#a84d5d';
  if (pct > -5) return '#bf4055';
  return '#d73751';
}

export function heatTextColor(pct: number | null): string {
  if (pct == null || Math.abs(pct) < 0.5) return 'rgb(var(--fg))';
  return '#ffffff';
}

export function heatSize(_adv: number, chgPct: number | null): { w: number; h: number } {
  const mag = Math.min(Math.abs(chgPct ?? 0), 8);
  const w = mag > 5 ? 150
    : mag > 3 ? 126
      : mag > 1.5 ? 104
        : mag > 0.5 ? 82
          : 60;
  const h = mag > 5 ? 94
    : mag > 3 ? 84
      : mag > 1.5 ? 70
        : mag > 0.5 ? 60
          : 52;

  return { w, h };
}

export const HEAT_LEGEND = [
  { label: '>+5%', color: '#00a972' },
  { label: '+1.5%', color: '#16775f' },
  { label: 'Flat', color: '#879295' },
  { label: '-1.5%', color: '#a84d5d' },
  { label: '<-5%', color: '#d73751' },
] as const;

export function heatWeight(pct: number | null): number {
  const mag = Math.abs(pct ?? 0);
  if (mag < 0.05) return 0.35;
  return Math.max(0.35, Math.min(mag, 8));
}

export function heatMoveSort(a: HeatMapEntry, b: HeatMapEntry): number {
  const move = Math.abs(b.chgPct ?? 0) - Math.abs(a.chgPct ?? 0);
  return move !== 0 ? move : a.symbol.localeCompare(b.symbol);
}

export function heatTone(pct: number | null): 'bull' | 'bear' | 'flat' | 'empty' {
  if (pct == null) return 'empty';
  if (pct > 0.5) return 'bull';
  if (pct < -0.5) return 'bear';
  return 'flat';
}

export function heatStats(entries: HeatMapEntry[]) {
  let gainers = 0;
  let losers = 0;
  let flat = 0;
  let totalMove = 0;
  let moveCount = 0;

  for (const entry of entries) {
    if (entry.chgPct == null) continue;
    if (entry.chgPct > 0.5) gainers += 1;
    else if (entry.chgPct < -0.5) losers += 1;
    else flat += 1;
    totalMove += entry.chgPct;
    moveCount += 1;
  }

  return {
    gainers,
    losers,
    flat,
    avgMove: moveCount ? totalMove / moveCount : null,
  };
}
