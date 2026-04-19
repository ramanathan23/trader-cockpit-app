'use client';

import { memo, useCallback, useMemo, useRef, useState } from 'react';
import { Activity } from 'lucide-react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { filterSignals, type Signal, type SignalCategory, type SignalType } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { DailyChart } from '@/components/dashboard/DailyChart';
import { OptionChainPanel } from '@/components/dashboard/OptionChainPanel';
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

const LatestSignalsBar = memo(({ signals, metricsCache, onChart }: {
  signals: Signal[];
  metricsCache: Record<string, InstrumentMetrics | null>;
  onChart: (sym: string) => void;
}) => {
  if (signals.length === 0) return null;

  return (
    <div className="flex shrink-0 gap-2 overflow-x-auto border-b border-border/60 bg-base/45 px-3 py-2">
      {signals.map(signal => (
        <button
          key={signal.id}
          type="button"
          onClick={() => onChart(signal.symbol)}
          className="flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-[10px] whitespace-nowrap transition-colors hover:bg-lift"
          title={`Open ${signal.symbol} chart`}
        >
          <span
            className="h-1.5 w-1.5 shrink-0 rounded-full"
            style={{ background: signal.direction === 'BULLISH' ? 'rgb(var(--bull))' : signal.direction === 'BEARISH' ? 'rgb(var(--bear))' : 'rgb(var(--ghost))' }}
          />
          <span className="font-black text-fg">{signal.symbol}</span>
          <span className="text-ghost">{signal.signal_type.replace(/_/g, ' ')}</span>
          {metricsCache[signal.symbol]?.is_fno && <span className="text-violet">F&O</span>}
        </button>
      ))}
    </div>
  );
});
LatestSignalsBar.displayName = 'LatestSignalsBar';

function ChartModal({
  symbol,
  metrics,
  onClose,
  onOptionChain,
}: {
  symbol: string;
  metrics?: InstrumentMetrics | null;
  onClose: () => void;
  onOptionChain: () => void;
}) {
  return (
    <div
      className="modal-backdrop"
      onClick={onClose}
      onKeyDown={event => { if (event.key === 'Escape') onClose(); }}
      tabIndex={-1}
    >
      <div
        className="surface-card max-h-[92vh] overflow-hidden"
        style={{ width: 940, maxWidth: '96vw' }}
        onClick={event => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-[15px] font-black text-fg">{symbol}</span>
            {metrics?.is_fno && <span className="chip" style={{ color: 'rgb(var(--violet))' }}>F&O</span>}
          </div>
          <div className="flex items-center gap-2">
            {metrics?.is_fno && (
              <button type="button" onClick={onOptionChain} className="seg-btn active" style={{ color: 'rgb(var(--accent))' }}>
                OC
              </button>
            )}
            <button type="button" onClick={onClose} className="icon-btn h-8 w-8" title="Close" aria-label="Close">x</button>
          </div>
        </div>
        <DailyChart symbol={symbol} height={460} />
      </div>
    </div>
  );
}

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
  const [chartSymbol, setChartSymbol] = useState<string | null>(null);
  const [ocSymbol, setOcSymbol] = useState<string | null>(null);

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
  const openChart = useCallback((sym: string) => setChartSymbol(sym), []);
  const openOC = useCallback((sym: string) => setOcSymbol(sym), []);

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
      {chartSymbol && (
        <ChartModal
          symbol={chartSymbol}
          metrics={metricsCache[chartSymbol]}
          onClose={() => setChartSymbol(null)}
          onOptionChain={() => {
            setChartSymbol(null);
            setOcSymbol(chartSymbol);
          }}
        />
      )}
      {ocSymbol && <OptionChainPanel symbol={ocSymbol} onClose={() => setOcSymbol(null)} />}
    </>
  );

  if (viewMode === 'table') {
    const items = tableVirtualizer.getVirtualItems();
    const total = tableVirtualizer.getTotalSize();

    return (
      <>
        <LatestSignalsBar signals={filtered.slice(0, 5)} metricsCache={metricsCache} onChart={openChart} />
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
      <LatestSignalsBar signals={filtered.slice(0, 5)} metricsCache={metricsCache} onChart={openChart} />
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
