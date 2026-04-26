import { ADMIN_CONFIG } from '@/lib/api-config';
import type { NavItem, ServiceConfigDef } from './adminTypes';

export const NAV: NavItem[] = [
  { key: 'full-sync',       label: 'Full Sync',  caption: 'Run full pipeline' },
  { key: 'zerodha',         label: 'Zerodha',    caption: 'Account login' },
  { key: 'token',           label: 'Token',      caption: 'Update Dhan token' },
  { key: 'config-scorer',   label: 'Ranking',    caption: 'Scoring params',    group: 'Config' },
  { key: 'config-datasync', label: 'Data Sync',  caption: 'Sync params',       group: 'Config' },
  { key: 'config-livefeed', label: 'Live Feed',  caption: 'Signal thresholds', group: 'Config' },
  { key: 'config-modeling', label: 'Modeling',   caption: 'Model params',       group: 'Config' },
];

export const PIPELINE_STEPS = [
  { key: 'zerodha',    label: 'Sync Zerodha',      endpoint: '/datasync/sync/run-zerodha-sse', method: 'POST' },
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
      { key: 'zerodha_performance_start_date', label: 'Performance start date', type: 'string', group: 'Zerodha' },
    ],
  },
  'config-livefeed': {
    id: 'livefeed', name: 'Live Feed', endpoint: ADMIN_CONFIG.LIVEFEED,
    fields: [
      { key: 'camarilla_vol_ratio',        label: 'Camarilla vol ratio',        type: 'float', min: 1,  max: 10,   group: 'Camarilla', step: 0.1 },
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
