'use client';

import { memo } from 'react';
import { cn } from '@/lib/cn';
import type { AppView } from './appTypes';
import { VIEWS } from './appTypes';

interface AppRailProps {
  view:          AppView;
  onView:        (v: AppView) => void;
  signalCount:   number;
  filteredCount: number;
}

export const AppRail = memo(({ view, onView, signalCount, filteredCount }: AppRailProps) => (
  <aside className="hidden w-[210px] shrink-0 border-r border-border bg-panel/72 p-3 md:block">
    <nav className="flex flex-col gap-1">
      {VIEWS.map(item => {
        const active = item.key === view;
        return (
          <button key={item.key} type="button" onClick={() => onView(item.key)}
            className={cn(
              'rounded-lg border px-3 py-3 text-left transition-colors',
              active
                ? 'border-accent/40 bg-accent/10 text-fg'
                : 'border-transparent text-dim hover:border-border hover:bg-lift/60 hover:text-fg',
            )}>
            <span className="block text-[12px] font-black">{item.label}</span>
            <span className="mt-0.5 block text-[10px] text-ghost">{item.caption}</span>
          </button>
        );
      })}
    </nav>

    <div className="mt-4 rounded-lg border border-border bg-base/50 p-3">
      <div className="text-[10px] font-black uppercase text-ghost">Tape</div>
      <div className="mt-2 flex items-end justify-between">
        <span className="num text-[22px] font-black text-fg">{filteredCount}</span>
        <span className="num text-[11px] text-ghost">of {signalCount}</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-border">
        <div className="h-full rounded-full bg-accent"
          style={{ width: `${signalCount ? Math.min(100, filteredCount / signalCount * 100) : 0}%` }} />
      </div>
    </div>
  </aside>
));
AppRail.displayName = 'AppRail';
