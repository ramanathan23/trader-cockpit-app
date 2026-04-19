'use client';

import { memo, useCallback, useMemo, useRef, useState } from 'react';
import { Activity } from 'lucide-react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { filterSignals, type Signal, type SignalCategory, type SignalType } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { SymbolModal } from '@/components/dashboard/SymbolModal';
import type { SymbolModalTab } from '@/components/dashboard/SymbolModal';
import { SignalCard } from './SignalCard';
import { SignalRow } from './SignalRow';

interface SignalFeedProps {
  signals: Signal[];
  metricsCache: Record<string, InstrumentMetrics | null>;
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

const TABLE_HEADERS: { h: string; title: string; align?: 'left' | 'right' | 'center' }[] = [
  { h: 'TIME', title: 'Signal trigger time' },
  { h: 'SYMBOL', title: 'Symbol and direction' },
  { h: 'TYPE', title: 'Signal type' },
  { h: 'PRICE', title: 'Trigger price', align: 'right' },
  { h: 'VOL', title: 'Volume ratio versus average', align: 'right' },
  { h: 'MTF', title: '15m and 1h bias' },
  { h: 'LEVELS', title: 'Entry, stop loss and target' },
  { h: 'ADV', title: 'Average daily traded value', align: 'right' },
  { h: 'CHG%', title: 'Change versus previous close', align: 'right' },
  { h: '52H%', title: 'Distance from 52-week high', align: 'right' },
  { h: 'SCORE', title: 'Composite score', align: 'right' },
  { h: 'NOTE', title: 'Private trading note' },
];

const NoteModal = memo(({ id, note, onSave, onClose }: {
  id: string;
  note?: string;
  onSave: (id: string, text: string) => void;
  onClose: () => void;
}) => {
  const [draft, setDraft] = useState(note ?? '');
  const commit = () => {
    onSave(id, draft);
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="surface-card w-80 p-4" onClick={event => event.stopPropagation()}>
        <p className="mb-2 text-[10px] font-black uppercase text-ghost">Note</p>
        <textarea
          autoFocus
          rows={4}
          value={draft}
          onChange={event => setDraft(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              commit();
            }
            if (event.key === 'Escape') onClose();
          }}
          placeholder="Add a trading note"
          className="field min-h-[84px] w-full resize-none py-2 text-[12px]"
          style={{ colorScheme: 'inherit' }}
        />
        <div className="mt-3 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="seg-btn">Cancel</button>
          <button type="button" onClick={commit} className="seg-btn active" style={{ color: 'rgb(var(--accent))' }}>Save</button>
        </div>
      </div>
    </div>
  );
});
NoteModal.displayName = 'NoteModal';


export const SignalFeed = memo(({
  signals,
  metricsCache,
  notes,
  onSaveNote,
  category,
  subType,
  fnoOnly,
  minAdvCr,
  viewMode,
  emptyLabel,
  hasMore,
  onLoadMore,
}: SignalFeedProps) => {
  const [noteModalId, setNoteModalId] = useState<string | null>(null);
  const [detailSymbol, setDetailSymbol] = useState<string | null>(null);
  const [detailTab, setDetailTab] = useState<SymbolModalTab>('chart');

  const filtered = useMemo(
    () => filterSignals(signals, category, minAdvCr, metricsCache, subType, fnoOnly),
    [signals, category, minAdvCr, metricsCache, subType, fnoOnly],
  );

  const tableParentRef = useRef<HTMLDivElement>(null);
  const tableVirtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => tableParentRef.current,
    estimateSize: () => 38,
    overscan: 16,
  });

  const cardParentRef = useRef<HTMLDivElement>(null);

  const loadMoreNearBottom = useCallback((element: HTMLDivElement | null, threshold: number) => {
    if (!element || !hasMore || !onLoadMore) return;
    if (element.scrollHeight - element.scrollTop - element.clientHeight < threshold) {
      onLoadMore();
    }
  }, [hasMore, onLoadMore]);

  const openNote = useCallback((id: string) => setNoteModalId(id), []);
  const openChart = useCallback((sym: string) => {
    setDetailSymbol(sym);
    setDetailTab('chart');
  }, []);
  const openOC = useCallback((sym: string) => {
    setDetailSymbol(sym);
    setDetailTab('oc');
  }, []);

  if (filtered.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-border bg-card text-ghost">
          <Activity size={22} aria-hidden="true" />
        </div>
        <span className="text-[13px] font-semibold text-dim">{emptyLabel ?? 'No signals'}</span>
      </div>
    );
  }

  const renderModals = () => (
    <>
      {noteModalId && (
        <NoteModal
          id={noteModalId}
          note={notes[noteModalId]}
          onSave={onSaveNote}
          onClose={() => setNoteModalId(null)}
        />
      )}
      {detailSymbol && (
        <SymbolModal
          symbol={detailSymbol}
          initialTab={detailTab}
          onClose={() => setDetailSymbol(null)}
        />
      )}
    </>
  );

  if (viewMode === 'table') {
    const items = tableVirtualizer.getVirtualItems();
    const total = tableVirtualizer.getTotalSize();

    return (
      <>
        <div
          ref={tableParentRef}
          className="table-wrap flex-1"
          onScroll={() => loadMoreNearBottom(tableParentRef.current, 220)}
        >
          <table className="data-table">
            <thead>
              <tr>
                {TABLE_HEADERS.map(({ h, title, align }) => (
                  <th key={h} title={title} className={align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.length > 0 && (
                <tr><td colSpan={TABLE_HEADERS.length} style={{ height: items[0].start, padding: 0, border: 'none' }} /></tr>
              )}
              {items.map(item => (
                <SignalRow
                  key={filtered[item.index].id}
                  signal={filtered[item.index]}
                  metrics={metricsCache[filtered[item.index].symbol]}
                  note={notes[filtered[item.index].id]}
                  onNoteClick={openNote}
                  onChart={openChart}
                  onOptionChain={openOC}
                />
              ))}
              {items.length > 0 && (
                <tr><td colSpan={TABLE_HEADERS.length} style={{ height: total - items[items.length - 1].end, padding: 0, border: 'none' }} /></tr>
              )}
            </tbody>
          </table>
        </div>
        {renderModals()}
      </>
    );
  }

  return (
    <>
      <div
        ref={cardParentRef}
        className="relative flex-1 overflow-y-auto p-3"
        onScroll={() => loadMoreNearBottom(cardParentRef.current, 420)}
      >
        <div className="signal-grid">
          {filtered.map(signal => (
            <SignalCard
              key={signal.id}
              signal={signal}
              metrics={metricsCache[signal.symbol]}
              note={notes[signal.id]}
              onSave={onSaveNote}
              onChart={openChart}
              onOptionChain={openOC}
            />
          ))}
        </div>
      </div>
      {renderModals()}
    </>
  );
});

SignalFeed.displayName = 'SignalFeed';
