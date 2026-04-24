import type { MarketPhase } from '@/domain/market';

export type AppView   = 'dashboard' | 'live' | 'history' | 'screener' | 'admin';
export type ThemeMode = 'dark' | 'light';

export type InitialConfigs = {
  scorer:   Record<string, unknown> | null;
  datasync: Record<string, unknown> | null;
  livefeed: Record<string, unknown> | null;
  modeling: Record<string, unknown> | null;
};

export const OPEN_PHASES = new Set<MarketPhase>(['DRIVE_WINDOW', 'EXECUTION', 'CLOSE_MOMENTUM']);

export const VIEWS: { key: AppView; label: string; caption: string }[] = [
  { key: 'dashboard', label: 'Dashboard', caption: 'Scored universe' },
  { key: 'live',      label: 'Live',      caption: 'Signal tape' },
  { key: 'history',   label: 'History',   caption: 'Replay session' },
  { key: 'screener',  label: 'Screener',  caption: 'Opportunity scan' },
  { key: 'admin',     label: 'Admin',     caption: 'Trigger jobs' },
];
