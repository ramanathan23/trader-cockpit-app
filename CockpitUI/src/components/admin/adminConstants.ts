import { ADMIN_CONFIG } from '@/lib/api-config';
import type { NavItem, ServiceConfigDef } from './adminTypes';

export const NAV: NavItem[] = [
  { key: 'full-sync',       label: 'Full Sync',  caption: 'Run full pipeline' },
  { key: 'zerodha',         label: 'Zerodha',    caption: 'Account login' },
  { key: 'token',           label: 'Token',      caption: 'Update Dhan token' },
  { key: 'config-datasync', label: 'Data Sync',  caption: 'Sync params',       group: 'Config' },
  { key: 'config-livefeed', label: 'Live Feed',  caption: 'Signal thresholds', group: 'Config' },
];

export const PIPELINE_STEPS = [
  { key: 'zerodha',    label: 'Sync Zerodha',    endpoint: '/datasync/sync/run-zerodha-sse', method: 'POST' },
  { key: 'sync-daily', label: 'Sync Daily Data', endpoint: '/datasync/sync/run-sse',         method: 'POST' },
  { key: 'sync-1min',  label: 'Sync 1-Min Data', endpoint: '/datasync/sync/run-1min-sse',    method: 'POST' },
] as const;

export const SERVICE_CONFIGS: Record<string, ServiceConfigDef> = {
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
    ],
  },
};
