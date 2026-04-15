'use client';

import { PHASE_STYLE, type Bias, type IndexName, type MarketPhase } from '@/domain/market';
import { unlockAudio } from '@/lib/audio';

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
}

export function Header({ phase, bias, clock }: HeaderProps) {
  const ps = PHASE_STYLE[phase] ?? PHASE_STYLE['--'];

  return (
    <header
      className="shrink-0 flex items-center justify-between px-5 py-2.5 bg-panel border-b border-border z-20"
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

      <div className="flex items-center gap-5">
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
                  style={{ color: up ? '#0dbd7d' : dn ? '#f23d55' : '#2a3f58' }}
                >
                  {idx.toUpperCase()}
                </span>
                <span
                  className="text-[13px] leading-none"
                  style={{ color: up ? '#0dbd7d' : dn ? '#f23d55' : '#2a3f58' }}
                >
                  {up ? '↑' : dn ? '↓' : '·'}
                </span>
              </div>
            );
          })}
        </div>

        {/* Divider */}
        <div className="hidden sm:block w-px h-4 bg-border" />

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

        {/* Clock */}
        <span className="num text-[11px] tabular-nums" style={{ color: '#2a3f58' }}>{clock}</span>
      </div>
    </header>
  );
}
