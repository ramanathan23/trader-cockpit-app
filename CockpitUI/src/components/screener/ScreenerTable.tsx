'use client';

import { memo, useCallback, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { ScreenerRow } from '@/domain/screener';
import { ScreenerTableHead, COLS } from './ScreenerTableHead';
import { ScreenerTableRow } from './ScreenerTableRow';

interface ScreenerTableProps {
  rows: ScreenerRow[];
  sortCol: string;
  sortAsc: boolean;
  onSort: (col: string) => void;
  loading: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  onChart?: (sym: string) => void;
  onOptionChain?: (sym: string) => void;
  marketOpen: boolean;
}

export const ScreenerTable = memo(({ rows, sortCol, sortAsc, onSort, loading, hasMore, onLoadMore, onChart, onOptionChain, marketOpen }: ScreenerTableProps) => {
  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 38,
    overscan: 20,
  });

  const handleScroll = useCallback(() => {
    const el = parentRef.current;
    if (!el || loading || !hasMore || !onLoadMore) return;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 220) onLoadMore();
  }, [loading, hasMore, onLoadMore]);

  if (loading && rows.length === 0) {
    return <div className="flex flex-1 items-center justify-center text-[13px] text-dim">Loading metrics</div>;
  }
  if (rows.length === 0) {
    return <div className="flex flex-1 items-center justify-center text-[13px] text-dim">No data matches the active filters.</div>;
  }

  const items = rowVirtualizer.getVirtualItems();
  const total = rowVirtualizer.getTotalSize();

  return (
    <div ref={parentRef} className="table-wrap flex-1" onScroll={handleScroll}>
      <table className="data-table">
        <ScreenerTableHead sortCol={sortCol} sortAsc={sortAsc} onSort={onSort} />
        <tbody>
          {items.length > 0 && <tr><td colSpan={COLS.length} style={{ height: items[0].start, padding: 0, border: 'none' }} /></tr>}
          {items.map(item => (
            <ScreenerTableRow key={rows[item.index].symbol} row={rows[item.index]}
              onChart={onChart} onOptionChain={onOptionChain} marketOpen={marketOpen} />
          ))}
          {items.length > 0 && <tr><td colSpan={COLS.length} style={{ height: total - items[items.length - 1].end, padding: 0, border: 'none' }} /></tr>}
        </tbody>
      </table>
    </div>
  );
});
ScreenerTable.displayName = 'ScreenerTable';
