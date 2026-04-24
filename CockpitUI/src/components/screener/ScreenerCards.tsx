'use client';

import { memo, useCallback, useRef } from 'react';
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
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        {rows.map(row => <ScreenerCard key={row.symbol} row={row} onChart={onChart} marketOpen={marketOpen} />)}
      </div>
    </div>
  );
});
ScreenerCards.displayName = 'ScreenerCards';
