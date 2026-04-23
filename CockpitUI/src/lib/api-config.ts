/**
 * Centralised API endpoint configuration.
 *
 * All service paths are relative — Next.js rewrites (next.config.ts) proxy
 * them to the correct backend service:
 *   /api/*          → LiveFeedService
 *   /scorer/*       → RankingService
 *   /indicators/*   → IndicatorsService
 *   /datasync/*     → DataSyncService
 *   /modeling/*     → ModelingService
 */

// ── LiveFeedService endpoints ────────────────────────────────────────────────

export const LIVE_FEED = {
  SIGNALS_WS:           '/api/v1/signals/ws',
  TOKEN_STATUS:         '/api/v1/token/status',
  INSTRUMENTS_METRICS:  '/api/v1/instruments/metrics',
  SCREENER:             '/api/v1/screener',
  SIGNAL_HISTORY:       '/api/v1/signals/history',
  SIGNAL_HISTORY_DATES: '/api/v1/signals/history/dates',
  OPTION_CHAIN_EXPIRIES:'/api/v1/optionchain/expiries',
  OPTION_CHAIN:         '/api/v1/optionchain',
} as const;

// ── RankingService endpoints ──────────────────────────────────────────────────

export const SCORER = {
  DASHBOARD:      '/scorer/dashboard',
  SCORES_COMPUTE: '/scorer/scores/compute',
  CONFIG:         '/scorer/config',
} as const;

// ── IndicatorsService endpoints ───────────────────────────────────────────────

export const INDICATORS = {
  COMPUTE:     '/indicators/compute',
  COMPUTE_SSE: '/indicators/compute-sse',
} as const;

// ── Admin config endpoints ────────────────────────────────────────────────────

export const ADMIN_CONFIG = {
  SCORER:   '/scorer/config',
  DATASYNC: '/datasync/config',
  LIVEFEED: '/api/v1/config',
  MODELING: '/modeling/config',
} as const;

// ── WebSocket URL helpers ────────────────────────────────────────────────────

function toWebSocketUrl(baseUrl: string): string {
  const url = new URL(baseUrl);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return url.toString();
}

function getLiveFeedBaseUrl(): string {
  if (typeof window === 'undefined') return 'http://localhost:8003';
  const url = new URL(window.location.origin);
  if (url.port === '3000') url.port = '8003';
  return url.toString().replace(/\/$/, '');
}

export function getSignalsWebSocketUrl(): string {
  const base = process.env.NEXT_PUBLIC_LIVE_FEED_URL ?? getLiveFeedBaseUrl();
  const normalized = base.endsWith('/') ? base.slice(0, -1) : base;
  return toWebSocketUrl(`${normalized}${LIVE_FEED.SIGNALS_WS}`);
}
