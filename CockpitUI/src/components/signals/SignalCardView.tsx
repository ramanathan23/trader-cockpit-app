'use client';

import { memo, useCallback, useEffect, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
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
  const [lanes, setLanes] = useState(1);
  const gap = 12;
  const cardWidth = `calc((100% - ${(lanes - 1) * gap}px) / ${lanes})`;
  const virtualizer = useVirtualizer({
    count: sortedFiltered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 210,
    overscan: lanes * 4,
    lanes,
  });

  useEffect(() => {
    const el = parentRef.current;
    if (!el) return;
    const update = () => {
      const minWidth = el.clientWidth <= 900 ? el.clientWidth : el.clientWidth <= 1280 ? 230 : 260;
      setLanes(Math.max(1, Math.floor((el.clientWidth - 24 + gap) / (minWidth + gap))));
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

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
        <div className="relative" style={{ height: virtualizer.getTotalSize() }}>
          {virtualizer.getVirtualItems().map(item => {
            const signal = sortedFiltered[item.index];
            return (
              <div
                key={signal.id}
                ref={virtualizer.measureElement}
                data-index={item.index}
                className="absolute top-0"
                style={{
                  left: `calc(${item.lane} * (${cardWidth} + ${gap}px))`,
                  width: cardWidth,
                  transform: `translateY(${item.start}px)`,
                }}
              >
                <SignalCard signal={signal}
                  metrics={metricsCache[signal.symbol]} marketOpen={marketOpen}
                  note={notes[signal.id]} onSave={onSave} onChart={onChart} onOptionChain={onOptionChain} />
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
});
SignalCardView.displayName = 'SignalCardView';
