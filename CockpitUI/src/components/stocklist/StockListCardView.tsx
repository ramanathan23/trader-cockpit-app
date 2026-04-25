'use client';

import { memo, useCallback, useEffect, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { StockRow } from '@/domain/stocklist';
import type { NoteEntry } from '@/hooks/useNotes';
import type { SymbolModalTab } from '@/components/dashboard/SymbolModal';
import type { LivePriceData } from '@/components/ui/LivePrice';
import { StockListCard } from './StockListCard';

interface StockListCardViewProps {
  rows:        StockRow[];
  livePrices:  Record<string, LivePriceData>;
  noteEntries: Record<string, NoteEntry[]>;
  onOpenModal: (symbol: string, tab: SymbolModalTab) => void;
  loading?:     boolean;
  hasMore?:     boolean;
  onLoadMore?:  () => void;
}

export const StockListCardView = memo(({
  rows, livePrices, noteEntries, onOpenModal, loading, hasMore, onLoadMore,
}: StockListCardViewProps) => {
  const parentRef = useRef<HTMLDivElement>(null);
  const [lanes, setLanes] = useState(1);
  const gap = 12;
  const cardWidth = `calc((100% - ${(lanes - 1) * gap}px) / ${lanes})`;
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 184,
    overscan: lanes * 4,
    lanes,
  });

  useEffect(() => {
    const el = parentRef.current;
    if (!el) return;
    const update = () => setLanes(Math.max(1, Math.floor((el.clientWidth - 32 + gap) / (240 + gap))));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const handleScroll = useCallback(() => {
    const el = parentRef.current;
    if (!el || loading || !hasMore || !onLoadMore) return;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 420) onLoadMore();
  }, [loading, hasMore, onLoadMore]);

  return (
    <div ref={parentRef} className="min-h-0 flex-1 overflow-y-auto p-4" onScroll={handleScroll}>
      <div className="relative" style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map(item => {
          const row = rows[item.index];
          return (
            <div
              key={row.symbol}
              ref={virtualizer.measureElement}
              data-index={item.index}
              className="absolute top-0"
              style={{
                left: `calc(${item.lane} * (${cardWidth} + ${gap}px))`,
                width: cardWidth,
                transform: `translateY(${item.start}px)`,
              }}
            >
              <StockListCard
                row={row}
                livePrice={livePrices[row.symbol]}
                noteCount={(noteEntries[row.symbol] ?? []).length}
                onOpenModal={tab => onOpenModal(row.symbol, tab)}
              />
            </div>
          );
        })}
        {rows.length === 0 && (
          <div className="py-16 text-center text-[12px] text-ghost">
            No results - adjust filters or refresh.
          </div>
        )}
      </div>
    </div>
  );
});
StockListCardView.displayName = 'StockListCardView';
