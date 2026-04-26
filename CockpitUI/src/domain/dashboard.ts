// Dashboard domain — types for unified scoring dashboard.

export interface DashboardStats {
  total_scored:    number;
  watchlist_count: number;
  avg_score:       number;
  max_score:       number;
  min_score:       number;
  high_conviction: number;
  above_average:   number;
  avg_iss_score?:  number | null;
  low_iss_watchlist_count?: number;
  score_date:      string;
  computed_at:     string;
}

export type IntradaySessionType = 'TREND_UP' | 'TREND_DOWN' | 'CHOP' | 'VOLATILE' | 'GAP_FADE' | 'NEUTRAL';

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
  comfort_score:          number | null;
  comfort_score_v2?:      number | null;
  comfort_score_v3?:      number | null;
  comfort_interpretation: string | null;
  iss_score?:             number | null;
  choppiness_idx?:        number | null;
  stop_hunt_rate?:        number | null;
  pullback_depth_hist?:   number | null;
  session_type_pred?:     IntradaySessionType | null;
  trend_up_prob?:         number | null;
  chop_prob?:             number | null;
  pullback_depth_pred?:   number | null;
}

export interface DashboardResponse {
  stats:  DashboardStats;
  scores: ScoredSymbol[];
}
