// Screener domain — types, filter logic, sort logic.
// Encapsulates all screener-specific data transformations as pure functions.

export interface ScreenerRow {
  symbol: string;
  adv_20_cr?: number;
  atr_14?: number;
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
  f52h?: number;  // % below 52-week high  (negative = below, 0 = at high)
  f52l?: number;  // % above 52-week low   (positive = above)
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

export function decorateRows(raw: Omit<ScreenerRow, 'f52h' | 'f52l'>[]): ScreenerRow[] {
  return raw.map(r => ({
    ...r,
    f52h: r.week52_high && r.prev_day_close
      ? (r.prev_day_close - r.week52_high) / r.week52_high * 100
      : undefined,
    f52l: r.week52_low && r.prev_day_close
      ? (r.prev_day_close - r.week52_low) / r.week52_low * 100
      : undefined,
  }));
}

export function applyFilters(
  rows: ScreenerRow[],
  query: string,
  range: ScreenerRangeFilter,
  presets: Set<ScreenerPreset>,
): ScreenerRow[] {
  const q = query.trim().toUpperCase();
  return rows.filter(r => {
    if (q && !r.symbol.includes(q)) return false;

    const adv = r.adv_20_cr ?? 0;
    if (adv < range.advMin) return false;
    if (range.advMax !== Infinity && adv > range.advMax) return false;

    const atr = r.atr_14 ?? 0;
    if (atr < range.atrMin) return false;
    if (range.atrMax !== Infinity && atr > range.atrMax) return false;

    const close = r.prev_day_close ?? 0;
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

export function isRangeActive(range: ScreenerRangeFilter): boolean {
  return (
    range.advMin > 0 || range.advMax !== Infinity ||
    range.atrMin > 0 || range.atrMax !== Infinity ||
    range.closeMin > 0 || range.closeMax !== Infinity ||
    range.f52hMin !== -Infinity || range.f52hMax !== Infinity ||
    range.f52lMin !== -Infinity || range.f52lMax !== Infinity
  );
}
