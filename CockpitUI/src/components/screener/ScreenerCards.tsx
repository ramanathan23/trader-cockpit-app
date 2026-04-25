'use client';

import { memo, useCallback, useEffect, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { ScreenerRow } from '@/domain/screener';
import { ScreenerCard } from './ScreenerCard';

interface ScreenerCardsProps {
  rows: ScreenerRow[];
  loading: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  onChart?: (sym: string) => void;
  marketOpen: boolean;
}

export const ScreenerCards = memo(({ rows, loading, hasMore, onLoadMore, onChart, marketOpen }: ScreenerCardsProps) => {
  const parentRef = useRef<HTMLDivElement>(null);
  const [lanes, setLanes] = useState(1);
  const gap = 12;
  const cardWidth = `calc((100% - ${(lanes - 1) * gap}px) / ${lanes})`;
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 186,
    overscan: lanes * 4,
    lanes,
  });

  useEffect(() => {
    const el = parentRef.current;
    if (!el) return;
    const update = () => {
      const minWidth = el.clientWidth >= 1536 ? 260 : el.clientWidth >= 640 ? 300 : el.clientWidth;
      setLanes(Math.max(1, Math.floor((el.clientWidth - 32 + gap) / (minWidth + gap))));
    };
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

  if (loading && rows.length === 0) {
    return <div className="flex flex-1 items-center justify-center text-[13px] text-dim">Loading metrics</div>;
  }
  if (rows.length === 0) {
    return <div className="flex flex-1 items-center justify-center text-[13px] text-dim">No data matches the active filters.</div>;
  }

  return (
    <div ref={parentRef} className="flex-1 overflow-y-auto p-4" onScroll={handleScroll}>
      <div className="relative" style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map(item => {
          const row = rows[item.index];
          return (
            <div
              key={row.symbol}
              className="absolute top-0"
              style={{
                left: `calc(${item.lane} * (${cardWidth} + ${gap}px))`,
                width: cardWidth,
                transform: `translateY(${item.start}px)`,
              }}
            >
              <ScreenerCard row={row} onChart={onChart} marketOpen={marketOpen} />
            </div>
          );
        })}
      </div>
    </div>
  );
});
ScreenerCards.displayName = 'ScreenerCards';
