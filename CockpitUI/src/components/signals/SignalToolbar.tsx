'use client';

import { memo } from 'react';
import { Trash2 } from 'lucide-react';
import { cn } from '@/lib/cn';
import { filterSignals, type Signal, type SignalCategory, type SignalType } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { SignalWorkspaceControls } from './SignalWorkspaceControls';

interface SignalToolbarProps {
  category: SignalCategory;
  onCategory: (c: SignalCategory) => void;
  subType: SignalType | null;
  onSubType: (t: SignalType | null) => void;
  fnoOnly: boolean;
  onFnoOnly: (v: boolean) => void;
  minAdvCr: number;
  onMinAdv: (cr: number) => void;
  signals: Signal[];
  metricsCache: Record<string, InstrumentMetrics | null>;
  paused: boolean;
  pendingCount: number;
  onTogglePause: () => void;
  onClear: () => void;
  activeView: 'dashboard' | 'live' | 'history' | 'screener' | 'admin';
  onViewChange: (v: 'dashboard' | 'live' | 'history' | 'screener' | 'admin') => void;
}

export const SignalToolbar = memo(({ category, onCategory, subType, onSubType, fnoOnly, onFnoOnly, minAdvCr, onMinAdv, signals, metricsCache, paused, pendingCount, onTogglePause, onClear, activeView, onViewChange }: SignalToolbarProps) => {
  const signalWorkspace = activeView === 'live' || activeView === 'history';
  const filtered = filterSignals(signals, category, minAdvCr, metricsCache, subType, fnoOnly);

  return (
    <div className="shrink-0 border-b border-border bg-panel/88 px-3 py-3 xl:px-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="seg-group md:hidden">
          {(['dashboard', 'live', 'history', 'screener', 'admin'] as const).map(view => (
            <button key={view} type="button" onClick={() => onViewChange(view)}
              className={cn('seg-btn', activeView === view && 'active text-accent')}>
              {view}
            </button>
          ))}
        </div>

        {signalWorkspace && (
          <SignalWorkspaceControls
            category={category} onCategory={onCategory}
            subType={subType} onSubType={onSubType}
            fnoOnly={fnoOnly} onFnoOnly={onFnoOnly}
            minAdvCr={minAdvCr} onMinAdv={onMinAdv} />
        )}

        <div className="ml-auto flex items-center gap-2">
          {signalWorkspace && (
            <>
              <span className="chip num hidden lg:inline-flex" title="Filtered signals / total signals">
                {filtered.length}/{signals.length}
              </span>
              <button type="button" onClick={onClear} className="icon-btn" title="Clear signal tape">
                <Trash2 size={15} />
              </button>
              <button type="button" onClick={onTogglePause}
                className={`h-8 rounded-lg border px-3 text-[11px] font-black transition-colors ${
                  paused ? 'border-amber/50 bg-amber/10 text-amber' : 'border-border bg-base/50 text-dim hover:border-rim hover:text-fg'
                }`}
                title={paused ? `${pendingCount} signals queued` : 'Pause incoming signals'}>
                {paused ? `Resume${pendingCount > 0 ? ` ${pendingCount}` : ''}` : 'Pause'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
});
SignalToolbar.displayName = 'SignalToolbar';
