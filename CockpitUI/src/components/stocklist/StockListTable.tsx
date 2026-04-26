'use client';

import { Fragment, memo, useCallback, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { StockRow } from '@/domain/stocklist';
import type { NoteEntry } from '@/hooks/useNotes';
import type { SymbolModalTab } from '@/components/dashboard/SymbolModal';
import type { LivePriceData } from '@/components/ui/LivePrice';
import { COL_SPAN } from './stocklistTypes';
import { StockListTableHead } from './StockListTableHead';
import { StockListRow } from './StockListRow';
import { StockListExpandedRow } from './StockListExpandedRow';

interface StockListTableProps {
  rows:           StockRow[];
  expandedSymbol: string | null;
  livePrices:     Record<string, LivePriceData>;
  noteEntries:    Record<string, NoteEntry[]>;
  sortCol:        string;
  sortAsc:        boolean;
  onSort:         (col: string) => void;
  onToggle:       (symbol: string) => void;
  onOpenModal:    (symbol: string, tab: SymbolModalTab) => void;
  onAddNote:      (symbol: string, text: string) => void;
  onDeleteNote:   (symbol: string, id: string)   => void;
  loading?:        boolean;
  hasMore?:        boolean;
  onLoadMore?:     () => void;
}

export const StockListTable = memo((props: StockListTableProps) => {
  const { rows, expandedSymbol, livePrices, noteEntries, sortCol, sortAsc,
          onSort, onToggle, onOpenModal, onAddNote, onDeleteNote,
          loading, hasMore, onLoadMore } = props;
  const parentRef = useRef<HTMLDivElement>(null);
  const estimateSize = useCallback(
    (index: number) => rows[index]?.symbol === expandedSymbol ? 240 : 38,
    [rows, expandedSymbol],
  );
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize,
    overscan: 18,
  });
  const items = virtualizer.getVirtualItems();
  const total = virtualizer.getTotalSize();

  const handleScroll = useCallback(() => {
    const el = parentRef.current;
    if (!el || loading || !hasMore || !onLoadMore) return;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 260) onLoadMore();
  }, [loading, hasMore, onLoadMore]);

  return (
    <div ref={parentRef} className="table-wrap min-h-0 flex-1" onScroll={handleScroll}>
      <table className="data-table text-[12px]">
        <StockListTableHead sortCol={sortCol} sortAsc={sortAsc} onSort={onSort} />
        <tbody>
          {items.length > 0 && <tr><td colSpan={COL_SPAN} style={{ height: items[0].start, padding: 0, border: 'none' }} /></tr>}
          {items.map(item => {
            const row = rows[item.index];
            return (
            <Fragment key={row.symbol}>
              <StockListRow
                row={row}
                livePrice={livePrices[row.symbol]}
                isExpanded={expandedSymbol === row.symbol}
                noteCount={(noteEntries[row.symbol] ?? []).length}
                onToggle={onToggle}
                onOpenModal={onOpenModal}
              />
              {expandedSymbol === row.symbol && (
                <StockListExpandedRow
                  row={row}
                  entries={noteEntries[row.symbol] ?? []}
                  onAdd={onAddNote}
                  onDelete={onDeleteNote}
                  onOpenModal={tab => onOpenModal(row.symbol, tab)}
                />
              )}
            </Fragment>
            );
          })}
          {items.length > 0 && <tr><td colSpan={COL_SPAN} style={{ height: total - items[items.length - 1].end, padding: 0, border: 'none' }} /></tr>}
          {rows.length === 0 && (
            <tr>
              <td colSpan={COL_SPAN} className="py-16 text-center text-[12px] text-ghost">
                No results — adjust filters or refresh.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
});
StockListTable.displayName = 'StockListTable';
