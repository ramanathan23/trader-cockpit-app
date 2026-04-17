'use client';

import { PHASE_STYLE, type Bias, type IndexName, type MarketPhase } from '@/domain/market';
import { unlockAudio } from '@/lib/audio';
import type { TokenStatus } from '@/hooks/useTokenStatus';

const PHASE_TITLES: Record<string, string> = {
  DRIVE_WINDOW:   'Drive Window (9:15–9:45): High-momentum open; best for trend-following entries',
  EXECUTION:      'Execution Phase (9:45–11:30): Primary trading session; signals are most reliable here',
  CLOSE_MOMENTUM: 'Close Momentum (2:30–3:15): Late-day directional move, often aligns with institutional flow',
  SESSION_END:    'Session End (3:15–3:30): Last-minute order flows; avoid initiating new positions',
  DEAD_ZONE:      'Dead Zone (11:30–2:30): Low conviction, sideways chop; reduce size and be selective',
  '--':           'Market closed or phase data unavailable',
};

interface HeaderProps {
  phase: MarketPhase;
  bias: Record<IndexName, Bias>;
  clock: string;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  tokenStatus?: TokenStatus | null;
}

export function Header({ phase, bias, clock, theme, onToggleTheme, tokenStatus }: HeaderProps) {
  const ps = PHASE_STYLE[phase] ?? PHASE_STYLE['--'];

  // Compute human-readable expiry label
  let tokenLabel = 'TOKEN';
  let tokenColor = 'rgb(var(--ghost))';
  let tokenTitle = 'Token status unknown';
  if (tokenStatus) {
    if (!tokenStatus.present) {
      tokenLabel = 'NO TOKEN';
      tokenColor = 'rgb(var(--bear))';
      tokenTitle = 'Dhan access token not set';
    } else if (tokenStatus.expired) {
      tokenLabel = 'TOKEN EXPIRED';
      tokenColor = 'rgb(var(--bear))';
      tokenTitle = tokenStatus.expires_at
        ? `Token expired at ${new Date(tokenStatus.expires_at).toLocaleString()}`
        : 'Token is expired';
    } else if (tokenStatus.expires_at) {
      const exp = new Date(tokenStatus.expires_at);
      const diffMs = exp.getTime() - Date.now();
      const diffH  = Math.floor(diffMs / 3_600_000);
      const diffM  = Math.floor((diffMs % 3_600_000) / 60_000);
      if (diffH < 1) {
        tokenLabel = `TOKEN ${diffM}m`;
        tokenColor = 'rgb(var(--warn, 220 170 0))';
      } else if (diffH < 24) {
        tokenLabel = `TOKEN ${diffH}h`;
        tokenColor = 'rgb(var(--bull))';
      } else {
        const diffD = Math.floor(diffH / 24);
        tokenLabel = `TOKEN ${diffD}d`;
        tokenColor = 'rgb(var(--bull))';
      }
      tokenTitle = `Token expires ${exp.toLocaleString()}`;
    } else {
      tokenLabel = 'TOKEN OK';
      tokenColor = 'rgb(var(--bull))';
      tokenTitle = 'Token present (no expiry info)';
    }
  }

  return (
    <header
      className="shrink-0 flex items-center justify-between gap-4 px-4 py-2.5 bg-panel border-b border-border z-20"
      onClick={unlockAudio}
      title="Click to unlock in-browser audio alerts"
    >
      {/* Brand */}
      <div className="flex items-center gap-2.5">
        {/* Accent dot */}
        <span className="w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
        <h1 className="text-[11px] font-bold tracking-[0.22em] text-fg uppercase select-none">
          Trader Cockpit
        </h1>
      </div>

      <div className="flex items-center gap-3 sm:gap-5">
        {/* Index bias — icon + name */}
        <div className="hidden sm:flex items-center gap-4">
          {(['nifty', 'banknifty', 'sensex'] as IndexName[]).map(idx => {
            const b = bias[idx];
            const up = b === 'BULLISH', dn = b === 'BEARISH';
            return (
              <div key={idx} className="flex items-center gap-1.5">
                <span
                  className="text-[9px] font-bold tracking-wider"
                  title={`${idx.toUpperCase()} bias: ${up ? 'Bullish — price above key moving averages' : dn ? 'Bearish — price below key moving averages' : 'Neutral — no clear direction'}`}
                  style={{ color: up ? 'rgb(var(--bull))' : dn ? 'rgb(var(--bear))' : 'rgb(var(--ghost))' }}
                >
                  {idx.toUpperCase()}
                </span>
                <span
                  className="text-[13px] leading-none"
                  style={{ color: up ? 'rgb(var(--bull))' : dn ? 'rgb(var(--bear))' : 'rgb(var(--ghost))' }}
                >
                  {up ? '↑' : dn ? '↓' : '·'}
                </span>
              </div>
            );
          })}
        </div>

        {/* Divider */}
        <div className="hidden sm:block w-px h-4 bg-border" />

        <button
          onClick={e => {
            e.stopPropagation();
            onToggleTheme();
          }}
          className="theme-chip flex items-center gap-1.5 rounded-md px-2 py-1 text-[9px] font-bold tracking-[0.14em] uppercase transition-colors"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
        >
          <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
        </button>

        {/* Phase badge */}
        <span
          className="text-[9px] font-black tracking-[0.14em] uppercase px-2.5 py-1 rounded select-none cursor-default"
          title={PHASE_TITLES[phase] ?? phase}
          style={{
            background: `${ps.color}14`,
            color:       ps.color,
            border:      `1px solid ${ps.color}30`,
          }}
        >
          {phase.replace(/_/g, ' ')}
        </span>

        {/* Token status */}
        <span
          className="num text-[9px] font-bold tracking-[0.12em] uppercase select-none cursor-default"
          style={{ color: tokenColor }}
          title={tokenTitle}
        >
          {tokenLabel}
        </span>

        {/* Clock */}
        <span className="num text-[11px] tabular-nums text-ghost">{clock}</span>
      </div>
    </header>
  );
}
