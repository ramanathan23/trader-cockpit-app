import type { MarketPhase } from '@/domain/market';

export type AppView   = 'stocks' | 'accounts' | 'live' | 'admin';
export type ThemeMode = 'dark' | 'light';

export type InitialConfigs = {
  datasync: Record<string, unknown> | null;
  livefeed: Record<string, unknown> | null;
};

export const OPEN_PHASES = new Set<MarketPhase>(['DRIVE_WINDOW', 'EXECUTION', 'CLOSE_MOMENTUM']);

export const VIEWS: { key: AppView; label: string; caption: string }[] = [
  { key: 'stocks',   label: 'Stocks',   caption: 'Universe + screener' },
  { key: 'accounts', label: 'Accounts', caption: 'Trades + performance' },
  { key: 'live',     label: 'Live',     caption: 'Signal tape' },
  { key: 'admin',    label: 'Admin',    caption: 'Trigger jobs' },
];
