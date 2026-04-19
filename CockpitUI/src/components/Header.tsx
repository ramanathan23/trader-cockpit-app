'use client';

import { PHASE_STYLE, type Bias, type IndexName, type MarketPhase } from '@/domain/market';
import { unlockAudio } from '@/lib/audio';
import type { TokenStatus } from '@/hooks/useTokenStatus';

const PHASE_TITLES: Record<string, string> = {
  DRIVE_WINDOW: '9:15-9:45. High-momentum open; trend entries need fast confirmation.',
  EXECUTION: '9:45-11:30. Primary execution window; signals have better context.',
  DEAD_ZONE: '11:30-14:30. Lower conviction, more chop, stricter selection.',
  CLOSE_MOMENTUM: '14:30-15:15. Late directional flow can resume.',
  SESSION_END: '15:15-15:30. Avoid fresh risk unless already planned.',
  '--': 'Market closed or phase unavailable.',
};

interface HeaderProps {
  phase: MarketPhase;
  bias: Record<IndexName, Bias>;
  clock: string;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  tokenStatus?: TokenStatus | null;
}

function ThemeIcon({ theme }: { theme: 'dark' | 'light' }) {
  if (theme === 'dark') {
    return (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M20 14.4A7.7 7.7 0 0 1 9.6 4a8.2 8.2 0 1 0 10.4 10.4Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 5V3m0 18v-2M5 12H3m18 0h-2M6.3 6.3 4.9 4.9m14.2 14.2-1.4-1.4m0-11.4 1.4-1.4M4.9 19.1l1.4-1.4M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function BiasPill({ name, value }: { name: IndexName; value: Bias }) {
  const bullish = value === 'BULLISH';
  const bearish = value === 'BEARISH';
  const color = bullish ? 'rgb(var(--bull))' : bearish ? 'rgb(var(--bear))' : 'rgb(var(--ghost))';
  const marker = bullish ? 'UP' : bearish ? 'DN' : 'FLAT';

  return (
    <span className="chip gap-1.5" title={`${name.toUpperCase()} bias: ${value}`}>
      <span className="text-[9px] text-ghost">{name.toUpperCase()}</span>
      <span className="num text-[10px]" style={{ color }}>{marker}</span>
    </span>
  );
}

function tokenMeta(tokenStatus?: TokenStatus | null) {
  if (!tokenStatus) {
    return { label: 'Token unknown', color: 'rgb(var(--ghost))', title: 'Dhan token status unavailable' };
  }

  if (!tokenStatus.present) {
    return { label: 'No token', color: 'rgb(var(--bear))', title: 'Dhan access token is not set' };
  }

  if (tokenStatus.expired) {
    return {
      label: 'Token expired',
      color: 'rgb(var(--bear))',
      title: tokenStatus.expires_at ? `Expired at ${new Date(tokenStatus.expires_at).toLocaleString()}` : 'Token expired',
    };
  }

  if (!tokenStatus.expires_at) {
    return { label: 'Token ok', color: 'rgb(var(--bull))', title: 'Token present; expiry unavailable' };
  }

  const expires = new Date(tokenStatus.expires_at);
  const ms = expires.getTime() - Date.now();
  const minutes = Math.max(0, Math.floor(ms / 60_000));
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (hours < 1) {
    return { label: `Token ${minutes}m`, color: 'rgb(var(--amber))', title: `Expires ${expires.toLocaleString()}` };
  }

  if (hours < 24) {
    return { label: `Token ${hours}h`, color: 'rgb(var(--bull))', title: `Expires ${expires.toLocaleString()}` };
  }

  return { label: `Token ${days}d`, color: 'rgb(var(--bull))', title: `Expires ${expires.toLocaleString()}` };
}

export function Header({ phase, bias, clock, theme, onToggleTheme, tokenStatus }: HeaderProps) {
  const ps = PHASE_STYLE[phase] ?? PHASE_STYLE['--'];
  const token = tokenMeta(tokenStatus);

  return (
    <header
      className="shrink-0 border-b border-border bg-panel/95 px-4 py-3 backdrop-blur"
      onClick={unlockAudio}
      title="Click once to enable browser audio alerts"
    >
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-accent/30 bg-accent/10 text-accent">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M4 17h4l3-10 4 10h5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M4 7h3m10 0h3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </span>
          <div className="min-w-0">
            <h1 className="truncate text-[14px] font-black uppercase text-fg">Trader Cockpit</h1>
            <p className="hidden text-[11px] text-ghost sm:block">Momentum, signals, option chain, and universe breadth</p>
          </div>
        </div>

        <div className="hidden min-w-0 flex-1 items-center gap-2 md:flex">
          {(['nifty', 'banknifty', 'sensex'] as IndexName[]).map(idx => (
            <BiasPill key={idx} name={idx} value={bias[idx]} />
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <span
            className="chip"
            title={PHASE_TITLES[phase] ?? String(phase)}
            style={{ color: ps.color, borderColor: `${ps.color}55`, background: `${ps.color}12` }}
          >
            {String(phase).replace(/_/g, ' ')}
          </span>

          <span className="chip hidden sm:inline-flex" title={token.title} style={{ color: token.color }}>
            {token.label}
          </span>

          <span className="chip num">{clock}</span>

          <button
            type="button"
            className="icon-btn"
            onClick={event => {
              event.stopPropagation();
              onToggleTheme();
            }}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          >
            <ThemeIcon theme={theme} />
          </button>
        </div>
      </div>
    </header>
  );
}
