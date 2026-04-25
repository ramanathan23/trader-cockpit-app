import type { ScreenerRow } from './screener';
import type { ScoredSymbol } from './dashboard';

export interface StockRow extends ScreenerRow {
  company_name?:          string | null;
  rank?:                  number;
  total_score?:           number;
  momentum_score?:        number;
  trend_score?:           number;
  volatility_score?:      number;
  structure_score?:       number;
  score_date?:            string;
  bb_squeeze?:            boolean | null;
  squeeze_days?:          number | null;
  nr7?:                   boolean | null;
  adx_14?:                number | null;
  rsi_14?:                number | null;
  comfort_score?:         number | null;
  comfort_interpretation?: string | null;
}

export function mergeStockRows(screenerRows: ScreenerRow[], scores: ScoredSymbol[]): StockRow[] {
  const scoreMap = new Map(scores.map(s => [s.symbol, s]));
  return screenerRows.map(r => {
    const s = scoreMap.get(r.symbol);
    if (!s) return { ...r } as StockRow;
    return {
      ...r,
      company_name:          s.company_name,
      rank:                  s.rank,
      total_score:           s.total_score,
      momentum_score:        s.momentum_score,
      trend_score:           s.trend_score,
      volatility_score:      s.volatility_score,
      structure_score:       s.structure_score,
      score_date:            s.score_date,
      bb_squeeze:            s.bb_squeeze,
      squeeze_days:          s.squeeze_days,
      nr7:                   s.nr7,
      adx_14:                s.adx_14,
      rsi_14:                s.rsi_14,
      comfort_score:         s.comfort_score,
      comfort_interpretation: s.comfort_interpretation,
      prev_day_close: r.prev_day_close ?? s.prev_day_close,
      atr_14:         r.atr_14         ?? s.atr_14,
      adv_20_cr:      r.adv_20_cr      ?? s.adv_20_cr,
      week52_high:    r.week52_high    ?? s.week52_high,
      week52_low:     r.week52_low     ?? s.week52_low,
      ema_50:         r.ema_50         ?? s.ema_50,
      ema_200:        r.ema_200        ?? s.ema_200,
      stage:          r.stage          ?? s.stage,
      weekly_bias:    r.weekly_bias    ?? s.weekly_bias,
    } as StockRow;
  });
}

export function sortStockRows(rows: StockRow[], col: string, asc: boolean): StockRow[] {
  return [...rows].sort((a, b) => {
    const av = (a as unknown as Record<string, unknown>)[col];
    const bv = (b as unknown as Record<string, unknown>)[col];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    const dir = asc ? 1 : -1;
    if (typeof av === 'string') return (av as string).localeCompare(bv as string) * dir;
    return ((av as number) < (bv as number) ? -1 : (av as number) > (bv as number) ? 1 : 0) * dir;
  });
}
