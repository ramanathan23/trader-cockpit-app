import { ADMIN_CONFIG } from '@/lib/api-config';
import type { NavItem, ServiceConfigDef } from './adminTypes';

export const NAV: NavItem[] = [
  { key: 'full-sync',       label: 'Full Sync',  caption: 'Run full pipeline' },
  { key: 'token',           label: 'Token',      caption: 'Update Dhan token' },
  { key: 'config-scorer',   label: 'Ranking',    caption: 'Scoring params',    group: 'Config' },
  { key: 'config-datasync', label: 'Data Sync',  caption: 'Sync params',       group: 'Config' },
  { key: 'config-livefeed', label: 'Live Feed',  caption: 'Signal thresholds', group: 'Config' },
  { key: 'config-modeling', label: 'Modeling',   caption: 'Model params',       group: 'Config' },
];

export const PIPELINE_STEPS = [
  { key: 'sync-daily',  label: 'Sync Daily Data',   endpoint: '/datasync/sync/run-sse',       method: 'POST' },
  { key: 'sync-1min',   label: 'Sync 1-Min Data',   endpoint: '/datasync/sync/run-1min-sse',  method: 'POST' },
  { key: 'indicators',  label: 'Compute Indicators', endpoint: '/indicators/compute-sse',      method: 'POST' },
  { key: 'scores',      label: 'Compute Rankings',   endpoint: '/scorer/scores/compute-sse',   method: 'POST' },
  { key: 'models',      label: 'Run Models',          endpoint: '/modeling/models',              method: 'GET'  },
] as const;

export const SERVICE_CONFIGS: Record<string, ServiceConfigDef> = {
  'config-scorer': {
    id: 'scorer', name: 'Ranking', endpoint: ADMIN_CONFIG.SCORER,
    fields: [
      { key: 'score_concurrency',      label: 'Parallel scoring workers',  type: 'int',   min: 1, max: 50 },
      { key: 'min_adv_crores',         label: 'Min ADV (₹Cr)',             type: 'float', min: 0, max: 100, step: 0.5 },
      { key: 'enable_comfort_scoring', label: 'Enable ML comfort scoring', type: 'bool' },
    ],
  },
  'config-datasync': {
    id: 'datasync', name: 'Data Sync', endpoint: ADMIN_CONFIG.DATASYNC,
    fields: [
      { key: 'sync_batch_size',        label: 'Symbols per batch',          type: 'int',   min: 1,   max: 500,   group: 'Sync' },
      { key: 'sync_batch_delay_s',     label: 'Batch delay (s)',            type: 'float', min: 0,   max: 30,    group: 'Sync',     step: 0.1 },
      { key: 'sync_1d_history_days',   label: 'Daily history window (days)',type: 'int',   min: 30,  max: 3650,  group: 'Sync' },
      { key: 'dhan_1min_rate_per_sec', label: 'Dhan 1-min req/sec',         type: 'int',   min: 1,   max: 20,    group: 'Dhan API' },
      { key: 'dhan_daily_budget',      label: 'Daily API budget',           type: 'int',   min: 100, max: 50000, group: 'Dhan API' },
      { key: 'dhan_budget_safety',     label: 'Budget safety buffer',       type: 'int',   min: 0,   max: 1000,  group: 'Dhan API' },
      { key: 'dhan_master_timeout_s',  label: 'Master CSV timeout (s)',     type: 'float', min: 5,   max: 120,   group: 'Dhan API', step: 1 },
    ],
  },
  'config-livefeed': {
    id: 'livefeed', name: 'Live Feed', endpoint: ADMIN_CONFIG.LIVEFEED,
    fields: [
      { key: 'drive_candles',               label: 'Drive candles',              type: 'int',   min: 2,  max: 20,   group: 'Open Drive' },
      { key: 'drive_min_body_ratio',        label: 'Min body ratio',             type: 'float', min: 0,  max: 1,    group: 'Open Drive', step: 0.05 },
      { key: 'drive_confirmed_thresh',      label: 'Confirmed threshold',        type: 'float', min: 0,  max: 1,    group: 'Open Drive', step: 0.05 },
      { key: 'drive_weak_thresh',           label: 'Weak threshold',             type: 'float', min: 0,  max: 1,    group: 'Open Drive', step: 0.05 },
      { key: 'spike_window',               label: 'Volume lookback window',     type: 'int',   min: 5,  max: 100,  group: 'Spike' },
      { key: 'spike_vol_ratio',            label: 'Volume multiplier',          type: 'float', min: 1,  max: 20,   group: 'Spike',      step: 0.1 },
      { key: 'spike_price_pct',            label: 'Min price move %',           type: 'float', min: 0,  max: 10,   group: 'Spike',      step: 0.1 },
      { key: 'spike_cooldown',             label: 'Candle cooldown',            type: 'int',   min: 1,  max: 50,   group: 'Spike' },
      { key: 'absorption_cooldown',        label: 'Absorption cooldown',        type: 'int',   min: 1,  max: 50,   group: 'Absorption' },
      { key: 'absorption_near_pct',        label: 'Near level distance',        type: 'float', min: 0,  max: 0.1,  group: 'Absorption', step: 0.001 },
      { key: 'exhaustion_downtrend_candles',label: 'Downtrend candles',         type: 'int',   min: 2,  max: 20,   group: 'Exhaustion' },
      { key: 'exhaustion_vol_ratio_min',   label: 'Climax vol ratio',           type: 'float', min: 1,  max: 30,   group: 'Exhaustion', step: 0.5 },
      { key: 'exhaustion_lower_lows',      label: 'Lower lows needed',          type: 'int',   min: 1,  max: 10,   group: 'Exhaustion' },
      { key: 'orb_vol_ratio',              label: 'ORB vol ratio',              type: 'float', min: 1,  max: 10,   group: 'Level Breakouts', step: 0.1 },
      { key: 'week52_vol_ratio',           label: '52-wk breakout vol ratio',   type: 'float', min: 1,  max: 10,   group: 'Level Breakouts', step: 0.1 },
      { key: 'camarilla_vol_ratio',        label: 'Camarilla vol ratio',        type: 'float', min: 1,  max: 10,   group: 'Level Breakouts', step: 0.1 },
      { key: 'vwap_vol_ratio',             label: 'VWAP vol ratio',             type: 'float', min: 1,  max: 10,   group: 'Level Breakouts', step: 0.1 },
      { key: 'vwap_hysteresis_min',        label: 'VWAP confirm candles',       type: 'int',   min: 1,  max: 20,   group: 'Level Breakouts' },
      { key: 'range_lookback',             label: 'Range lookback bars',        type: 'int',   min: 2,  max: 30,   group: 'Range' },
      { key: 'range_vol_ratio',            label: 'Range vol ratio',            type: 'float', min: 1,  max: 10,   group: 'Range',    step: 0.1 },
      { key: 'range_max_pct',              label: 'Max range width %',          type: 'float', min: 0,  max: 0.1,  group: 'Range',    step: 0.001 },
      { key: 'min_adv_cr',                 label: 'Min ADV (₹Cr)',              type: 'float', min: 0,  max: 100,  group: 'Noise',    step: 0.5 },
      { key: 'cluster_max_per_candle',     label: 'Max signals/candle',         type: 'int',   min: 1,  max: 20,   group: 'Noise' },
      { key: 'confluence_15m_candles',     label: '15m candles',                type: 'int',   min: 1,  max: 20,   group: 'Confluence' },
      { key: 'confluence_1h_candles',      label: '1h candles',                 type: 'int',   min: 1,  max: 50,   group: 'Confluence' },
      { key: 'confluence_min_move_pct',    label: 'Min move %',                 type: 'float', min: 0,  max: 5,    group: 'Confluence', step: 0.01 },
      { key: 'candle_minutes',             label: 'Candle size (min)',           type: 'int',   min: 1,  max: 60,   group: 'Feed' },
      { key: 'dhan_ws_batch_size',         label: 'WS subscription batch',      type: 'int',   min: 50, max: 1000, group: 'Feed' },
      { key: 'dhan_reconnect_delay_s',     label: 'WS reconnect delay (s)',     type: 'float', min: 1,  max: 60,   group: 'Feed',     step: 0.5 },
      { key: 'candle_write_batch_size',    label: 'Candle write batch',         type: 'int',   min: 10, max: 1000, group: 'Feed' },
      { key: 'candle_write_flush_s',       label: 'Candle flush interval (s)',  type: 'float', min: 1,  max: 30,   group: 'Feed',     step: 0.5 },
    ],
  },
  'config-modeling': {
    id: 'modeling', name: 'Modeling', endpoint: ADMIN_CONFIG.MODELING,
    fields: [
      { key: 'auto_retrain_enabled',                   label: 'Auto-retrain enabled',     type: 'bool' },
      { key: 'max_model_age_days',                     label: 'Max model age (days)',      type: 'int',   min: 1,   max: 365 },
      { key: 'training_concurrency',                   label: 'Training concurrency',     type: 'int',   min: 1,   max: 8 },
      { key: 'score_concurrency',                      label: 'Scoring concurrency',      type: 'int',   min: 1,   max: 100 },
      { key: 'comfort_scorer_retrain_threshold_rmse',  label: 'RMSE retrain threshold',   type: 'float', min: 0,   max: 50,     group: 'Comfort Scorer', step: 0.5 },
      { key: 'comfort_scorer_shadow_days',             label: 'Shadow transition days',   type: 'int',   min: 1,   max: 30,     group: 'Comfort Scorer' },
      { key: 'comfort_scorer_min_train_samples',       label: 'Min training samples',     type: 'int',   min: 100, max: 500000, group: 'Comfort Scorer' },
      { key: 'regime_classifier_cache_ttl',            label: 'Regime cache TTL (s)',     type: 'int',   min: 30,  max: 3600,   group: 'Regime Classifier' },
      { key: 'pattern_detector_confidence_threshold',  label: 'Pattern confidence',       type: 'float', min: 0,   max: 1,      group: 'Pattern Detector', step: 0.05 },
    ],
  },
};
