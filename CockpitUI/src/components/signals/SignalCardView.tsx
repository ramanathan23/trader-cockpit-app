'use client';

import { memo, useCallback, useRef } from 'react';
import type { Signal } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { SignalCard } from './SignalCard';

interface SignalCardViewProps {
  sortedFiltered: Signal[];
  filteredCount: number;
  metricsCache: Record<string, InstrumentMetrics | null>;
  marketOpen: boolean;
  notes: Record<string, string>;
  onSave: (id: string, text: string) => void;
  onChart: (sym: string) => void;
  onOptionChain: (sym: string) => void;
  query: string;
  setQuery: (q: string) => void;
  hasMore?: boolean;
  onLoadMore?: () => void;
}

export const SignalCardView = memo(({ sortedFiltered, filteredCount, metricsCache, marketOpen, notes, onSave, onChart, onOptionChain, query, setQuery, hasMore, onLoadMore }: SignalCardViewProps) => {
  const parentRef = useRef<HTMLDivElement>(null);

  const handleScroll = useCallback(() => {
    const el = parentRef.current;
    if (!el || !hasMore || !onLoadMore) return;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 420) onLoadMore();
  }, [hasMore, onLoadMore]);

  return (
    <>
      <div className="flex shrink-0 items-center gap-3 border-b border-border bg-panel/72 px-4 py-2">
        <input type="text" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search symbol"
          className="field w-40 text-[12px]" style={{ colorScheme: 'inherit' }} />
        <span className="num text-[11px] text-ghost">{sortedFiltered.length}/{filteredCount}</span>
        {query && (
          <button type="button" onClick={() => setQuery('')}
            className="text-[11px] font-bold text-ghost hover:text-fg">Clear</button>
        )}
      </div>
      <div ref={parentRef} className="relative flex-1 overflow-y-auto p-3" onScroll={handleScroll}>
        <div className="signal-grid">
          {sortedFiltered.map(signal => (
            <SignalCard key={signal.id} signal={signal}
              metrics={metricsCache[signal.symbol]} marketOpen={marketOpen}
              note={notes[signal.id]} onSave={onSave} onChart={onChart} onOptionChain={onOptionChain} />
          ))}
        </div>
      </div>
    </>
  );
});
SignalCardView.displayName = 'SignalCardView';
