export interface HeatMapEntry {
  symbol:  string;
  adv:     number;         // ADV in Cr — controls cell width
  chgPct:  number | null;  // day change % — controls cell color + height
  score?:  number;
  stage?:  string;
}

export function heatChgColor(pct: number | null): string {
  if (pct == null) return 'rgba(51,65,85,0.50)';
  if (pct >  5)   return 'rgba(22,163,74,1.00)';
  if (pct >  3)   return 'rgba(22,163,74,0.82)';
  if (pct >  1.5) return 'rgba(22,163,74,0.58)';
  if (pct >  0.5) return 'rgba(34,197,94,0.38)';
  if (pct > -0.5) return 'rgba(71,85,105,0.55)';
  if (pct > -1.5) return 'rgba(239,68,68,0.38)';
  if (pct > -3)   return 'rgba(220,38,38,0.62)';
  if (pct > -5)   return 'rgba(220,38,38,0.84)';
  return 'rgba(185,28,28,1.00)';
}

export function heatTextColor(pct: number | null): string {
  if (pct == null || Math.abs(pct) < 0.5) return 'rgba(148,163,184,0.85)';
  return '#ffffff';
}

/** Width from ADV tier (Cr). Height from |chgPct| magnitude. Area ∝ ADV × move. */
export function heatSize(adv: number, chgPct: number | null): { w: number; h: number } {
  const w = adv > 5000 ? 160
          : adv > 2000 ? 134
          : adv > 800  ? 110
          : adv > 250  ? 90
          : adv > 80   ? 74
          : adv > 20   ? 60
          : 48;

  const mag = Math.min(Math.abs(chgPct ?? 0), 8);
  const h   = mag > 5   ? 90
            : mag > 3   ? 74
            : mag > 1.5 ? 60
            : mag > 0.5 ? 50
            : 42;

  return { w, h };
}

export const HEAT_LEGEND = [
  { label: '>+5%',  color: 'rgba(22,163,74,1.00)'  },
  { label: '+1.5%', color: 'rgba(22,163,74,0.58)'  },
  { label: 'Flat',  color: 'rgba(71,85,105,0.55)'  },
  { label: '-1.5%', color: 'rgba(220,38,38,0.62)'  },
  { label: '<-5%',  color: 'rgba(185,28,28,1.00)'  },
] as const;
