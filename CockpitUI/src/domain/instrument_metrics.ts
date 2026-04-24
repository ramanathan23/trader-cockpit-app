// Instrument metrics domain — real-time and daily reference data per symbol.

export interface InstrumentMetrics {
  symbol: string;
  is_fno?: boolean;
  day_high?: number;
  day_low?: number;
  day_open?: number;
  day_close?: number;
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
