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
  if (pct == null) return 'linear-gradient(135deg, rgb(var(--lift)), rgb(var(--card)))';
  if (pct > 5) return 'linear-gradient(135deg, #04945f, #19c985)';
  if (pct > 3) return 'linear-gradient(135deg, #087f5b, #16b97b)';
  if (pct > 1.5) return 'linear-gradient(135deg, #116f58, #0ea66f)';
  if (pct > 0.5) return 'linear-gradient(135deg, #1d5f54, #17815f)';
  if (pct > -0.5) return 'linear-gradient(135deg, rgb(var(--lift)), #33424a)';
  if (pct > -1.5) return 'linear-gradient(135deg, #6f3842, #9b3e4d)';
  if (pct > -3) return 'linear-gradient(135deg, #863340, #c44154)';
  if (pct > -5) return 'linear-gradient(135deg, #9c2f40, #dd4558)';
  return 'linear-gradient(135deg, #8f2334, #ef4058)';
}

export function heatTextColor(pct: number | null): string {
  if (pct == null || Math.abs(pct) < 0.5) return 'rgb(var(--fg))';
  return '#ffffff';
}

export function heatSize(adv: number, chgPct: number | null): { w: number; h: number } {
  const w = adv > 5000 ? 160
    : adv > 2000 ? 134
      : adv > 800 ? 110
        : adv > 250 ? 90
          : adv > 80 ? 74
            : adv > 20 ? 60
              : 48;

  const mag = Math.min(Math.abs(chgPct ?? 0), 8);
  const h = mag > 5 ? 98
    : mag > 3 ? 84
      : mag > 1.5 ? 70
        : mag > 0.5 ? 60
          : 52;

  return { w, h };
}

export const HEAT_LEGEND = [
  { label: '>+5%', color: '#19c985' },
  { label: '+1.5%', color: '#0ea66f' },
  { label: 'Flat', color: '#33424a' },
  { label: '-1.5%', color: '#c44154' },
  { label: '<-5%', color: '#ef4058' },
] as const;

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
