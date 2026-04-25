'use client';

import { Activity, HelpCircle, Moon, Sun } from 'lucide-react';
import { PHASE_STYLE, type Bias, type IndexName, type MarketPhase } from '@/domain/market';
import { unlockAudio } from '@/lib/audio';
import { PHASE_TITLES, tokenMeta } from '@/lib/headerUtils';
import type { TokenStatus } from '@/hooks/useTokenStatus';
import { ViewToggle } from '@/components/ui/ViewToggle';
import { BiasPill } from '@/components/ui/BiasPill';

interface HeaderProps {
  phase: MarketPhase;
  bias: Record<IndexName, Bias>;
  clock: string;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  tokenStatus?: TokenStatus | null;
  viewMode: 'card' | 'table' | 'heatmap';
  onViewMode: (v: 'card' | 'table' | 'heatmap') => void;
  showViewToggle: boolean;
  showHelp: boolean;
  onToggleHelp: () => void;
}

export function Header({ phase, bias, clock, theme, onToggleTheme, tokenStatus, viewMode, onViewMode, showViewToggle, showHelp, onToggleHelp }: HeaderProps) {
  const ps    = PHASE_STYLE[phase] ?? PHASE_STYLE['--'];
  const token = tokenMeta(tokenStatus);

  return (
    <header className="shrink-0 border-b border-border bg-panel/95 px-4 py-3 backdrop-blur"
      onClick={unlockAudio} title="Click once to enable browser audio alerts">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-accent/30 bg-accent/10 text-accent">
            <Activity size={18} />
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
          <span className="chip" title={PHASE_TITLES[phase] ?? String(phase)}
            style={{ color: ps.color, borderColor: `${ps.color}55`, background: `${ps.color}12` }}>
            {String(phase).replace(/_/g, ' ')}
          </span>
          <span className="chip hidden sm:inline-flex" title={token.title} style={{ color: token.color }}>
            {token.label}
          </span>
          <span className="chip num">{clock}</span>
          {showViewToggle && <ViewToggle view={viewMode} onChange={onViewMode} />}
          <button type="button" onClick={e => { e.stopPropagation(); onToggleHelp(); }}
            title={showHelp ? 'Hide glossary' : 'Show glossary'}
            className={`icon-btn ${showHelp ? 'border-accent/50 bg-accent/10 text-accent' : ''}`}>
            <HelpCircle size={15} />
          </button>
          <button type="button" className="icon-btn" onClick={e => { e.stopPropagation(); onToggleTheme(); }}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
            {theme === 'dark' ? <Moon size={15} /> : <Sun size={15} />}
          </button>
        </div>
      </div>
    </header>
  );
}
