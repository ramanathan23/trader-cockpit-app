// Market domain — types and phase styling constants.

export type MarketPhase =
  | 'DRIVE_WINDOW'
  | 'EXECUTION'
  | 'CLOSE_MOMENTUM'
  | 'SESSION_END'
  | 'DEAD_ZONE'
  | '--';

export type IndexName = 'nifty' | 'banknifty' | 'sensex';
export type Bias = 'BULLISH' | 'BEARISH' | 'NEUTRAL';

export interface MarketStatus {
  phase: MarketPhase;
  bias: Record<IndexName, Bias>;
}

export const PHASE_STYLE: Record<MarketPhase, { bg: string; color: string }> = {
  DRIVE_WINDOW:   { bg: '#0dbd7d14', color: '#0dbd7d' },
  EXECUTION:      { bg: '#0dbd7d10', color: '#0a9e68' },
  CLOSE_MOMENTUM: { bg: '#2d7ee814', color: '#2d7ee8' },
  SESSION_END:    { bg: '#f23d5514', color: '#f23d55' },
  DEAD_ZONE:      { bg: '#e8933a14', color: '#e8933a' },
  '--':           { bg: '#2a3f5814', color: '#2a3f58' },
};
