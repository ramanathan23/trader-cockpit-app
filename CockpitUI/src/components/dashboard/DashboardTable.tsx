'use client';

import { useRef } from 'react';
import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-react';
import { cn } from '@/lib/cn';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { ScoredSymbol } from '@/domain/dashboard';
import type { LivePriceData } from '@/components/ui/LivePrice';
import { DASHBOARD_HEADERS, type SortKey } from './dashboardTypes';
import { ScoreRow } from './ScoreRow';
import type { SymbolModalTab } from './SymbolModal';

interface DashboardTableProps {
  rows: ScoredSymbol[];
  livePrices: Record<string, LivePriceData>;
  marketOpen: boolean;
  sortKey: SortKey;
  sortAsc: boolean;
  onSort: (key: SortKey) => void;
  onOpen: (sym: string, tab?: SymbolModalTab) => void;
  emptyMsg: string;
}

/** Virtualized table for scored symbols — handles large lists efficiently. */
export function DashboardTable({ rows, livePrices, marketOpen, sortKey, sortAsc, onSort, onOpen, emptyMsg }: DashboardTableProps) {
  const parentRef     = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({ count: rows.length, getScrollElement: () => parentRef.current, estimateSize: () => 44, overscan: 12 });
  const items         = rowVirtualizer.getVirtualItems();
  const totalSize     = rowVirtualizer.getTotalSize();

  return (
    <div ref={parentRef} className="table-wrap flex-1">
      <table className="data-table">
        <thead>
          <tr>
            {DASHBOARD_HEADERS.map(h => (
              <th key={h.key} title={h.title}
                onClick={() => h.sortable && onSort(h.key as SortKey)}
                className={cn(h.align === 'right' ? 'text-right' : h.align === 'center' ? 'text-center' : 'text-left', h.sortable && 'cursor-pointer hover:text-fg', sortKey === h.key && 'text-accent')}>
                <span className="inline-flex items-center gap-0.5">
                  {h.label}
                  {h.sortable && (
                    <span className="inline-flex opacity-60">
                      {sortKey === h.key
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
          {items.length > 0 && <tr><td colSpan={DASHBOARD_HEADERS.length} style={{ height: items[0].start, padding: 0, border: 'none' }} /></tr>}
          {items.map(item => (
            <ScoreRow
              key={rows[item.index].symbol}
              row={rows[item.index]}
              livePrice={livePrices[rows[item.index].symbol]}
              marketOpen={marketOpen}
              onOpen={onOpen}
            />
          ))}
          {items.length > 0 && <tr><td colSpan={DASHBOARD_HEADERS.length} style={{ height: totalSize - items[items.length - 1].end, padding: 0, border: 'none' }} /></tr>}
        </tbody>
      </table>
      {rows.length === 0 && <div className="flex h-48 items-center justify-center text-[13px] text-dim">{emptyMsg}</div>}
    </div>
  );
}
