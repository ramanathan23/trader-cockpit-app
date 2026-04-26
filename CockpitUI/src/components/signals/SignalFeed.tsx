'use client';

import { memo, useCallback, useMemo, useState } from 'react';
import { Activity } from 'lucide-react';
import type { Signal, SignalCategory, SignalType } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { SymbolModal } from '@/components/dashboard/SymbolModal';
import type { SymbolModalTab } from '@/components/dashboard/SymbolModal';
import { useLivePrices } from '@/hooks/useLivePrices';
import { useSignalSort } from './useSignalSort';
import { SignalTableView } from './SignalTableView';
import { SignalCardView } from './SignalCardView';
import { NoteModal } from './NoteModal';

interface SignalFeedProps {
  signals: Signal[];
  metricsCache: Record<string, InstrumentMetrics | null>;
  marketOpen: boolean;
  notes: Record<string, string>;
  onSaveNote: (id: string, text: string) => void;
  category: SignalCategory;
  subType?: SignalType | null;
  fnoOnly?: boolean;
  minAdvCr: number;
  viewMode: 'card' | 'table';
  emptyLabel?: string;
  hasMore?: boolean;
  onLoadMore?: () => void;
}

export const SignalFeed = memo(({ signals, metricsCache, marketOpen, notes, onSaveNote, category, subType, fnoOnly, minAdvCr, viewMode, emptyLabel, hasMore, onLoadMore }: SignalFeedProps) => {
  const liveSymbols = useMemo(() => [...new Set(signals.map(signal => signal.symbol))], [signals]);
  const livePrices = useLivePrices(liveSymbols, marketOpen && liveSymbols.length > 0);
  const displayMetrics = useMemo(() => {
    const next = { ...metricsCache };
    for (const [symbol, price] of Object.entries(livePrices)) {
      const base = next[symbol];
      if (!base || price.ltp == null) continue;
      const prev = price.prevClose ?? base.prev_day_close;
      next[symbol] = {
        ...base,
        current_price: price.ltp,
        day_close: price.ltp,
        prev_day_close: prev ?? base.prev_day_close,
        day_chg_pct: prev ? (price.ltp - prev) / prev * 100 : base.day_chg_pct,
      };
    }
    return next;
  }, [livePrices, metricsCache]);

  const { query, setQuery, sortKey, sortAsc, handleSort, clearSort, filtered, sortedFiltered } =
    useSignalSort({ signals, category, minAdvCr, metricsCache: displayMetrics, subType, fnoOnly });

  const [noteModalId,  setNoteModalId]  = useState<string | null>(null);
  const [detailSymbol, setDetailSymbol] = useState<string | null>(null);
  const [detailTab,    setDetailTab]    = useState<SymbolModalTab>('chart');

  const openNote  = useCallback((id: string) => setNoteModalId(id), []);
  const openChart = useCallback((sym: string) => { setDetailSymbol(sym); setDetailTab('chart'); }, []);
  const openOC    = useCallback((sym: string) => { setDetailSymbol(sym); setDetailTab('oc'); }, []);

  if (filtered.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-border bg-card text-ghost">
          <Activity size={22} />
        </div>
        <span className="text-[13px] font-semibold text-dim">{emptyLabel ?? 'No signals'}</span>
      </div>
    );
  }

  const sharedProps = { metricsCache: displayMetrics, marketOpen, notes, onChart: openChart, onOptionChain: openOC, query, setQuery, hasMore, onLoadMore };

  return (
    <>
      {viewMode === 'table'
        ? <SignalTableView sortedFiltered={sortedFiltered} filteredCount={filtered.length}
            onNoteClick={openNote} sortKey={sortKey} sortAsc={sortAsc} handleSort={handleSort} clearSort={clearSort} {...sharedProps} />
        : <SignalCardView sortedFiltered={sortedFiltered} filteredCount={filtered.length}
            onSave={onSaveNote} {...sharedProps} />}

      {noteModalId  && <NoteModal id={noteModalId} note={notes[noteModalId]} onSave={onSaveNote} onClose={() => setNoteModalId(null)} />}
      {detailSymbol && <SymbolModal symbol={detailSymbol} initialTab={detailTab} onClose={() => setDetailSymbol(null)} />}
    </>
  );
});
SignalFeed.displayName = 'SignalFeed';
