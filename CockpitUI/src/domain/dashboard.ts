// Dashboard domain — types for unified scoring dashboard.

export interface DashboardStats {
  total_scored:    number;
  watchlist_count: number;
  avg_score:       number;
  max_score:       number;
  min_score:       number;
  high_conviction: number;
  above_average:   number;
  avg_execution_score?:  number | null;
  low_execution_watchlist_count?: number;
  score_date:      string;
  computed_at:     string;
}

export interface ScoredSymbol {
  symbol:           string;
  company_name:     string | null;
  is_fno:           boolean | null;
  score_date:       string;
  total_score:      number;
  momentum_score:   number;
  trend_score:      number;
  volatility_score: number;
  structure_score:  number;
  rank:             number;
  is_watchlist:     boolean;
  is_new_watchlist: boolean;
  computed_at:      string;
  // From symbol_metrics join
  prev_day_close:   number | null;
  atr_14:           number | null;
  adv_20_cr:        number | null;
  week52_high:      number | null;
  week52_low:       number | null;
  ema_50:           number | null;
  ema_200:          number | null;
  bb_squeeze:       boolean | null;
  squeeze_days:     number | null;
  nr7:              boolean | null;
  adx_14:           number | null;
  rsi_14:           number | null;
  weekly_bias:      string | null;
  stage:            string | null;
  execution_score?:          number | null;
  execution_grade?:          string | null;
  breakout_quality_score?:   number | null;
  breakdown_quality_score?:  number | null;
  reversal_quality_score?:   number | null;
  fakeout_rate?:             number | null;
  deep_pullback_rate?:       number | null;
  avg_adverse_excursion_r?:  number | null;
  avg_pullback_depth_r?:     number | null;
  liquidity_score?:          number | null;
  avg_session_turnover_cr?:  number | null;
  setups_analyzed?:          number | null;
}

export interface DashboardResponse {
  stats:  DashboardStats;
  scores: ScoredSymbol[];
}
