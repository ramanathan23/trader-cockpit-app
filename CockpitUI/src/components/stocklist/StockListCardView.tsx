'use client';

import { memo } from 'react';
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
}

export const StockListCardView = memo(({ rows, livePrices, noteEntries, onOpenModal }: StockListCardViewProps) => (
  <div className="min-h-0 flex-1 overflow-y-auto p-4">
    <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-3">
      {rows.map(row => (
        <StockListCard
          key={row.symbol}
          row={row}
          livePrice={livePrices[row.symbol]}
          noteCount={(noteEntries[row.symbol] ?? []).length}
          onOpenModal={tab => onOpenModal(row.symbol, tab)}
        />
      ))}
      {rows.length === 0 && (
        <div className="col-span-full py-16 text-center text-[12px] text-ghost">
          No results — adjust filters or refresh.
        </div>
      )}
    </div>
  </div>
));
StockListCardView.displayName = 'StockListCardView';
