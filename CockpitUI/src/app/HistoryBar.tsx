'use client';

import { memo } from 'react';
import { cn } from '@/lib/cn';

interface HistoryBarProps {
  date:    string;
  dates:   string[];
  loading: boolean;
  onDate:  (d: string) => void;
}

export const HistoryBar = memo(({ date, dates, loading, onDate }: HistoryBarProps) => (
  <div className="shrink-0 border-b border-border bg-panel/80 px-4 py-3">
    <div className="flex flex-wrap items-center gap-3">
      <span className="text-[10px] font-black uppercase text-ghost">Replay date</span>
      <input type="date" value={date} onChange={e => onDate(e.target.value)}
        className="field h-8 text-[12px]" style={{ colorScheme: 'inherit' }} />
      {dates.length > 0 && (
        <div className="seg-group">
          {dates.slice(0, 7).map(d => (
            <button key={d} type="button" onClick={() => onDate(d)}
              className={cn('seg-btn', date === d && 'active text-accent')}>
              {d.slice(5)}
            </button>
          ))}
        </div>
      )}
      {loading && <span className="num text-[11px] text-amber">Loading</span>}
    </div>
  </div>
));
HistoryBar.displayName = 'HistoryBar';
