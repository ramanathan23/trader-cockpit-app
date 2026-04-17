// Screener domain — types, filter logic, sort logic.
// Encapsulates all screener-specific data transformations as pure functions.

export interface ScreenerRow {
  symbol: string;
  is_fno?: boolean;
  adv_20_cr?: number;
  atr_14?: number;
  current_price?: number;
  daily_vwap?: number;
  ema_50?: number;
  ema_200?: number;
  week_return_pct?: number;
  week_gain_pct?: number;
  week_decline_pct?: number;
  prev_day_close?: number;
  prev_day_high?: number;
  prev_day_low?: number;
  week52_high?: number;
  week52_low?: number;
  prev_week_high?: number;
  prev_week_low?: number;
  prev_month_high?: number;
  prev_month_low?: number;
  // Derived fields added client-side
  display_price?: number;
  f52h?: number;  // % below 52-week high  (negative = below, 0 = at high)
  f52l?: number;  // % above 52-week low   (positive = above)
  dvwap_delta_pct?: number;
  ema50_delta_pct?: number;
  ema200_delta_pct?: number;
}

export interface ScreenerBreadthStat {
  key: string;
  label: string;
  count: number;
  eligible: number;
  pct: number;
}

export interface ScreenerRangeFilter {
  advMin: number;
  advMax: number;
  atrMin: number;
  atrMax: number;
  closeMin: number;
  closeMax: number;
  f52hMin: number;
  f52hMax: number;
  f52lMin: number;
  f52lMax: number;
}

export const DEFAULT_RANGE: ScreenerRangeFilter = {
  advMin:  0,         advMax:  Infinity,
  atrMin:  0,         atrMax:  Infinity,
  closeMin: 0,        closeMax: Infinity,
  f52hMin: -Infinity, f52hMax: Infinity,
  f52lMin: -Infinity, f52lMax: Infinity,
};

export type ScreenerPreset = 'near52h' | 'near52l' | 'nearpdh' | 'nearpdl';

export const SCREENER_PRESETS: { key: ScreenerPreset; label: string }[] = [
  { key: 'near52h', label: 'NEAR 52H' },
  { key: 'near52l', label: 'NEAR 52L' },
  { key: 'nearpdh', label: 'NEAR PDH' },
  { key: 'nearpdl', label: 'NEAR PDL' },
];

// ── Pure helpers ─────────────────────────────────────────────────────────────

export function rowPrice(row: Pick<ScreenerRow, 'current_price' | 'prev_day_close'>): number | undefined {
  return row.current_price ?? row.prev_day_close;
}

function pctFromReference(price?: number, reference?: number): number | undefined {
  if (price == null || reference == null || reference === 0) return undefined;
  return (price - reference) / reference * 100;
}

export function decorateRows(raw: Omit<ScreenerRow, 'display_price' | 'f52h' | 'f52l' | 'dvwap_delta_pct' | 'ema50_delta_pct' | 'ema200_delta_pct'>[]): ScreenerRow[] {
  return raw.map(r => ({
    ...r,
    display_price: rowPrice(r),
    f52h: pctFromReference(rowPrice(r), r.week52_high),
    f52l: pctFromReference(rowPrice(r), r.week52_low),
    dvwap_delta_pct: pctFromReference(rowPrice(r), r.daily_vwap),
    ema50_delta_pct: pctFromReference(rowPrice(r), r.ema_50),
    ema200_delta_pct: pctFromReference(rowPrice(r), r.ema_200),
  }));
}

function ratio(count: number, eligible: number): number {
  return eligible > 0 ? count / eligible * 100 : 0;
}

export function computeBreadthStats(rows: ScreenerRow[]): ScreenerBreadthStat[] {
  const aboveDvwapEligible = rows.filter(r => r.display_price != null && r.daily_vwap != null);
  const aboveEma50Eligible = rows.filter(r => r.display_price != null && r.ema_50 != null);
  const aboveEma200Eligible = rows.filter(r => r.display_price != null && r.ema_200 != null);
  const positiveWeekEligible = rows.filter(r => r.week_return_pct != null);

  const aboveDvwap = aboveDvwapEligible.filter(r => (r.dvwap_delta_pct ?? Number.NEGATIVE_INFINITY) > 0).length;
  const aboveEma50 = aboveEma50Eligible.filter(r => (r.ema50_delta_pct ?? Number.NEGATIVE_INFINITY) > 0).length;
  const aboveEma200 = aboveEma200Eligible.filter(r => (r.ema200_delta_pct ?? Number.NEGATIVE_INFINITY) > 0).length;
  const positiveWeek = positiveWeekEligible.filter(r => (r.week_return_pct ?? Number.NEGATIVE_INFINITY) > 0).length;

  return [
    {
      key: 'dvwap',
      label: 'Above DVWAP',
      count: aboveDvwap,
      eligible: aboveDvwapEligible.length,
      pct: ratio(aboveDvwap, aboveDvwapEligible.length),
    },
    {
      key: 'ema50',
      label: 'Above 50 EMA',
      count: aboveEma50,
      eligible: aboveEma50Eligible.length,
      pct: ratio(aboveEma50, aboveEma50Eligible.length),
    },
    {
      key: 'ema200',
      label: 'Above 200 EMA',
      count: aboveEma200,
      eligible: aboveEma200Eligible.length,
      pct: ratio(aboveEma200, aboveEma200Eligible.length),
    },
    {
      key: 'week',
      label: 'Positive Week',
      count: positiveWeek,
      eligible: positiveWeekEligible.length,
      pct: ratio(positiveWeek, positiveWeekEligible.length),
    },
  ];
}

export function applyFilters(
  rows: ScreenerRow[],
  query: string,
  range: ScreenerRangeFilter,
  presets: Set<ScreenerPreset>,
  fnoOnly: boolean,
): ScreenerRow[] {
  const q = query.trim().toUpperCase();
  return rows.filter(r => {
    if (fnoOnly && !r.is_fno) return false;
    if (q && !r.symbol.includes(q)) return false;

    const adv = r.adv_20_cr ?? 0;
    if (adv < range.advMin) return false;
    if (range.advMax !== Infinity && adv > range.advMax) return false;

    const atr = r.atr_14 ?? 0;
    if (atr < range.atrMin) return false;
    if (range.atrMax !== Infinity && atr > range.atrMax) return false;

    const close = r.display_price ?? 0;
    if (close < range.closeMin) return false;
    if (range.closeMax !== Infinity && close > range.closeMax) return false;

    if (r.f52h != null) {
      if (range.f52hMin !== -Infinity && r.f52h < range.f52hMin) return false;
      if (range.f52hMax !== Infinity  && r.f52h > range.f52hMax) return false;
    }
    if (r.f52l != null) {
      if (range.f52lMin !== -Infinity && r.f52l < range.f52lMin) return false;
      if (range.f52lMax !== Infinity  && r.f52l > range.f52lMax) return false;
    }

    // Preset filters apply as AND combinations
    if (presets.has('near52h') && !(r.f52h != null && r.f52h >= -5)) return false;
    if (presets.has('near52l') && !(r.f52l != null && r.f52l >= 0 && r.f52l <= 10)) return false;
    if (presets.has('nearpdh') && !(
      r.prev_day_high && r.prev_day_close &&
      Math.abs((r.prev_day_close - r.prev_day_high) / r.prev_day_high) < 0.005
    )) return false;
    if (presets.has('nearpdl') && !(
      r.prev_day_low && r.prev_day_close &&
      Math.abs((r.prev_day_close - r.prev_day_low) / r.prev_day_low) < 0.005
    )) return false;

    return true;
  });
}

export function sortRows(rows: ScreenerRow[], col: string, asc: boolean): ScreenerRow[] {
  return [...rows].sort((a, b) => {
    const av = (a as unknown as Record<string, unknown>)[col] ?? (col === 'symbol' ? '' : -Infinity);
    const bv = (b as unknown as Record<string, unknown>)[col] ?? (col === 'symbol' ? '' : -Infinity);
    const dir = asc ? 1 : -1;
    if (typeof av === 'string') return (av as string).localeCompare(bv as string) * dir;
    return ((av as number) < (bv as number) ? -1 : (av as number) > (bv as number) ? 1 : 0) * dir;
  });
}

export function isRangeActive(range: ScreenerRangeFilter, fnoOnly = false): boolean {
  return (
    fnoOnly ||
    range.advMin > 0 || range.advMax !== Infinity ||
    range.atrMin > 0 || range.atrMax !== Infinity ||
    range.closeMin > 0 || range.closeMax !== Infinity ||
    range.f52hMin !== -Infinity || range.f52hMax !== Infinity ||
    range.f52lMin !== -Infinity || range.f52lMax !== Infinity
  );
}
