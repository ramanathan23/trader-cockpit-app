'use client';

import { memo, useCallback, useMemo, useRef, useState } from 'react';
import { Activity, ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-react';
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

type SignalSortKey = 'timestamp' | 'price' | 'volume_ratio' | 'score' | 'adv' | 'chg_pct' | 'f52h_pct';

const TABLE_HEADERS: { h: string; title: string; align?: 'left' | 'right' | 'center'; sortKey?: SignalSortKey }[] = [
  { h: 'TIME', title: 'Signal trigger time', sortKey: 'timestamp' },
  { h: 'SYMBOL', title: 'Symbol and direction' },
  { h: 'TYPE', title: 'Signal type' },
  { h: 'PRICE', title: 'Trigger price', align: 'right', sortKey: 'price' },
  { h: 'VOL', title: 'Volume ratio versus average', align: 'right', sortKey: 'volume_ratio' },
  { h: 'MTF', title: '15m and 1h bias' },
  { h: 'LEVELS', title: 'Entry, stop loss and target' },
  { h: 'ADV', title: 'Average daily traded value', align: 'right', sortKey: 'adv' },
  { h: 'CHG%', title: 'Change versus previous close', align: 'right', sortKey: 'chg_pct' },
  { h: '52H%', title: 'Distance from 52-week high', align: 'right', sortKey: 'f52h_pct' },
  { h: 'SCORE', title: 'Composite score', align: 'right', sortKey: 'score' },
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
  marketOpen,
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
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState<SignalSortKey | null>(null);
  const [sortAsc, setSortAsc] = useState(false);

  const handleSort = useCallback((key: SignalSortKey) => {
    setSortAsc(prev => sortKey === key ? !prev : key === 'timestamp');
    setSortKey(key);
  }, [sortKey]);

  const filtered = useMemo(
    () => filterSignals(signals, category, minAdvCr, metricsCache, subType, fnoOnly),
    [signals, category, minAdvCr, metricsCache, subType, fnoOnly],
  );

  const sortedFiltered = useMemo(() => {
    const q = query.trim().toUpperCase();
    const base = q ? filtered.filter(s => s.symbol.includes(q)) : filtered;
    if (!sortKey) return base;
    return [...base].sort((a, b) => {
      let av: number | null = null;
      let bv: number | null = null;
      const ma = metricsCache[a.symbol];
      const mb = metricsCache[b.symbol];
      switch (sortKey) {
        case 'timestamp': av = new Date(a.timestamp).getTime(); bv = new Date(b.timestamp).getTime(); break;
        case 'price': av = a.price ?? null; bv = b.price ?? null; break;
        case 'volume_ratio': av = a.volume_ratio ?? null; bv = b.volume_ratio ?? null; break;
        case 'score': av = a.score ?? null; bv = b.score ?? null; break;
        case 'adv': av = ma?.adv_20_cr ?? null; bv = mb?.adv_20_cr ?? null; break;
        case 'chg_pct': av = ma?.day_chg_pct ?? null; bv = mb?.day_chg_pct ?? null; break;
        case 'f52h_pct':
          av = ma?.week52_high != null && a.price != null ? (a.price / ma.week52_high - 1) * 100 : null;
          bv = mb?.week52_high != null && b.price != null ? (b.price / mb.week52_high - 1) * 100 : null;
          break;
      }
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return sortAsc ? av - bv : bv - av;
    });
  }, [filtered, query, sortKey, sortAsc, metricsCache]);

  const tableParentRef = useRef<HTMLDivElement>(null);
  const tableVirtualizer = useVirtualizer({
    count: sortedFiltered.length,
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
        <div className="flex shrink-0 items-center gap-3 border-b border-border bg-panel/72 px-4 py-2">
          <input
            type="text"
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder="Search symbol"
            className="field w-40 text-[12px]"
            style={{ colorScheme: 'inherit' }}
          />
          <span className="num text-[11px] text-ghost">{sortedFiltered.length}/{filtered.length}</span>
          {(query || sortKey) && (
            <button
              type="button"
              onClick={() => { setQuery(''); setSortKey(null); setSortAsc(false); }}
              className="text-[11px] font-bold text-ghost hover:text-fg"
            >
              Clear
            </button>
          )}
        </div>
        <div
          ref={tableParentRef}
          className="table-wrap flex-1"
          onScroll={() => loadMoreNearBottom(tableParentRef.current, 220)}
        >
          <table className="data-table">
            <thead>
              <tr>
                {TABLE_HEADERS.map(({ h, title, align, sortKey: sk }) => (
                  <th
                    key={h}
                    title={title}
                    onClick={() => sk && handleSort(sk)}
                    className={`${align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'} ${sk ? 'cursor-pointer hover:text-fg' : ''}`}
                    style={{ color: sortKey === sk && sk ? 'rgb(var(--accent))' : undefined }}
                  >
                    <span className="inline-flex items-center gap-0.5">
                      {h}
                      {sk && (
                        <span className="inline-flex opacity-60">
                          {sortKey === sk
                            ? sortAsc
                              ? <ChevronUp size={11} aria-hidden="true" />
                              : <ChevronDown size={11} aria-hidden="true" />
                            : <ChevronsUpDown size={11} className="opacity-50" aria-hidden="true" />
                          }
                        </span>
                      )}
                    </span>
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
                  key={sortedFiltered[item.index].id}
                  signal={sortedFiltered[item.index]}
                  metrics={metricsCache[sortedFiltered[item.index].symbol]}
                  marketOpen={marketOpen}
                  note={notes[sortedFiltered[item.index].id]}
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
          {sortedFiltered.length === 0 && (
            <div className="flex h-32 items-center justify-center text-[13px] text-dim">
              No signals match &ldquo;{query}&rdquo;
            </div>
          )}
        </div>
        {renderModals()}
      </>
    );
  }

  return (
    <>
      <div className="flex shrink-0 items-center gap-3 border-b border-border bg-panel/72 px-4 py-2">
        <input
          type="text"
          value={query}
          onChange={event => setQuery(event.target.value)}
          placeholder="Search symbol"
          className="field w-40 text-[12px]"
          style={{ colorScheme: 'inherit' }}
        />
        <span className="num text-[11px] text-ghost">{sortedFiltered.length}/{filtered.length}</span>
        {query && (
          <button
            type="button"
            onClick={() => setQuery('')}
            className="text-[11px] font-bold text-ghost hover:text-fg"
          >
            Clear
          </button>
        )}
      </div>
      <div
        ref={cardParentRef}
        className="relative flex-1 overflow-y-auto p-3"
        onScroll={() => loadMoreNearBottom(cardParentRef.current, 420)}
      >
        <div className="signal-grid">
          {sortedFiltered.map(signal => (
            <SignalCard
              key={signal.id}
              signal={signal}
              metrics={metricsCache[signal.symbol]}
              marketOpen={marketOpen}
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
