'use client';

import { Fragment, memo } from 'react';
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
}

export const StockListTable = memo((props: StockListTableProps) => {
  const { rows, expandedSymbol, livePrices, noteEntries, sortCol, sortAsc,
          onSort, onToggle, onOpenModal, onAddNote, onDeleteNote } = props;

  return (
    <div className="table-wrap min-h-0 flex-1">
      <table className="data-table text-[12px]">
        <StockListTableHead sortCol={sortCol} sortAsc={sortAsc} onSort={onSort} />
        <tbody>
          {rows.map(row => (
            <Fragment key={row.symbol}>
              <StockListRow
                row={row}
                livePrice={livePrices[row.symbol]}
                isExpanded={expandedSymbol === row.symbol}
                noteCount={(noteEntries[row.symbol] ?? []).length}
                onToggle={() => onToggle(row.symbol)}
                onOpenModal={tab => onOpenModal(row.symbol, tab)}
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
          ))}
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
