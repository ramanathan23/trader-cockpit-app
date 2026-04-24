'use client';

import { memo, useCallback, useRef } from 'react';
import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-react';
import { cn } from '@/lib/cn';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { Signal } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { SignalRow } from './SignalRow';
import { TABLE_HEADERS, type SignalSortKey } from './useSignalSort';

interface SignalTableViewProps {
  sortedFiltered: Signal[];
  filteredCount: number;
  metricsCache: Record<string, InstrumentMetrics | null>;
  marketOpen: boolean;
  notes: Record<string, string>;
  onNoteClick: (id: string) => void;
  onChart: (sym: string) => void;
  onOptionChain: (sym: string) => void;
  query: string;
  setQuery: (q: string) => void;
  sortKey: SignalSortKey | null;
  sortAsc: boolean;
  handleSort: (key: SignalSortKey) => void;
  clearSort: () => void;
  hasMore?: boolean;
  onLoadMore?: () => void;
}

export const SignalTableView = memo(({ sortedFiltered, filteredCount, metricsCache, marketOpen, notes, onNoteClick, onChart, onOptionChain, query, setQuery, sortKey, sortAsc, handleSort, clearSort, hasMore, onLoadMore }: SignalTableViewProps) => {
  const parentRef  = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({ count: sortedFiltered.length, getScrollElement: () => parentRef.current, estimateSize: () => 38, overscan: 16 });
  const items = virtualizer.getVirtualItems();
  const total = virtualizer.getTotalSize();

  const handleScroll = useCallback(() => {
    const el = parentRef.current;
    if (!el || !hasMore || !onLoadMore) return;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 220) onLoadMore();
  }, [hasMore, onLoadMore]);

  return (
    <>
      <div className="flex shrink-0 items-center gap-3 border-b border-border bg-panel/72 px-4 py-2">
        <input type="text" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search symbol"
          className="field w-40 text-[12px]" style={{ colorScheme: 'inherit' }} />
        <span className="num text-[11px] text-ghost">{sortedFiltered.length}/{filteredCount}</span>
        {(query || sortKey) && (
          <button type="button" onClick={() => { setQuery(''); clearSort(); }}
            className="text-[11px] font-bold text-ghost hover:text-fg">Clear</button>
        )}
      </div>
      <div ref={parentRef} className="table-wrap flex-1" onScroll={handleScroll}>
        <table className="data-table">
          <thead>
            <tr>
              {TABLE_HEADERS.map(({ h, title, align, sortKey: sk }) => (
                <th key={h} title={title} onClick={() => sk && handleSort(sk)}
                  className={cn(align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left', sk && 'cursor-pointer hover:text-fg', sortKey === sk && sk && 'text-accent')}>
                  <span className="inline-flex items-center gap-0.5">
                    {h}
                    {sk && (
                      <span className="inline-flex opacity-60">
                        {sortKey === sk
                          ? sortAsc ? <ChevronUp size={11} /> : <ChevronDown size={11} />
                          : <ChevronsUpDown size={11} className="opacity-50" />}
                      </span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.length > 0 && <tr><td colSpan={TABLE_HEADERS.length} style={{ height: items[0].start, padding: 0, border: 'none' }} /></tr>}
            {items.map(item => (
              <SignalRow key={sortedFiltered[item.index].id}
                signal={sortedFiltered[item.index]}
                metrics={metricsCache[sortedFiltered[item.index].symbol]}
                marketOpen={marketOpen}
                note={notes[sortedFiltered[item.index].id]}
                onNoteClick={onNoteClick} onChart={onChart} onOptionChain={onOptionChain} />
            ))}
            {items.length > 0 && <tr><td colSpan={TABLE_HEADERS.length} style={{ height: total - items[items.length - 1].end, padding: 0, border: 'none' }} /></tr>}
          </tbody>
        </table>
        {sortedFiltered.length === 0 && (
          <div className="flex h-32 items-center justify-center text-[13px] text-dim">No signals match &ldquo;{query}&rdquo;</div>
        )}
      </div>
    </>
  );
});
SignalTableView.displayName = 'SignalTableView';
