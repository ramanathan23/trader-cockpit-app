'use client';

import { memo, useCallback, useMemo, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { filterSignals, type Signal, type SignalCategory } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { SignalCard } from './SignalCard';
import { SignalRow } from './SignalRow';
import { DailyChart } from '@/components/dashboard/DailyChart';
import { OptionChainPanel } from '@/components/dashboard/OptionChainPanel';

interface SignalFeedProps {
  signals: Signal[];
  metricsCache: Record<string, InstrumentMetrics | null>;
  notes: Record<string, string>;
  onSaveNote: (id: string, text: string) => void;
  category: SignalCategory;
  minAdvCr: number;
  viewMode: 'card' | 'table';
  emptyLabel?: string;
  hasMore?: boolean;
  onLoadMore?: () => void;
}

// Minimal modal for editing note from table row
const NoteModal = memo(({ id, note, onSave, onClose }: {
  id: string; note?: string; onSave: (id: string, text: string) => void; onClose: () => void;
}) => {
  const [draft, setDraft] = useState(note ?? '');
  const commit = () => { onSave(id, draft); onClose(); };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(5,12,24,0.85)' }} onClick={onClose}>
      <div className="w-80 bg-card border border-border rounded-md p-4" style={{ boxShadow: '0 4px 40px rgba(0,0,0,0.7)' }} onClick={e => e.stopPropagation()}>
        <p className="text-[10px] font-bold tracking-[0.14em] uppercase mb-2" style={{ color: '#1e2e4a' }}>NOTE</p>
        <textarea
          autoFocus
          rows={3}
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commit(); } if (e.key === 'Escape') onClose(); }}
          placeholder="Add a trading note…"
          className="w-full border border-border rounded-sm text-[11px] text-fg px-2 py-1.5 resize-none focus:outline-none"
          style={{ background: '#050c18', colorScheme: 'dark' }}
        />
        <div className="flex gap-2 justify-end mt-2">
          <button onClick={onClose} className="text-[10px] transition-colors px-2 py-1" style={{ color: '#2a3f58' }}>Cancel</button>
          <button onClick={commit}  className="text-[10px] font-bold px-2 py-1" style={{ color: '#2d7ee8' }}>Save</button>
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
    <div className="flex gap-2 px-3 py-1.5 border-b border-border/40 overflow-x-auto shrink-0">
      {signals.map(s => (
        <button
          key={s.id}
          onClick={() => onChart(s.symbol)}
          className="flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] whitespace-nowrap hover:bg-border/20 transition-colors"
        >
          <span
            className="w-1.5 h-1.5 rounded-full shrink-0"
            style={{ background: s.direction === 'BULLISH' ? '#22c55e' : s.direction === 'BEARISH' ? '#ef4444' : '#4b5563' }}
          />
          <span className="font-bold text-fg">{s.symbol}</span>
          <span style={{ color: '#2a3f58' }}>{s.signal_type.replace(/_/g, ' ')}</span>
          {metricsCache[s.symbol]?.is_fno && (
            <span className="text-[7px] font-black px-0.5" style={{ color: '#9b72f7' }}>F&O</span>
          )}
        </button>
      ))}
    </div>
  );
});
LatestSignalsBar.displayName = 'LatestSignalsBar';

const TABLE_HEADERS: { h: string; title: string }[] = [
  { h: 'TIME',   title: 'Signal trigger time (IST)' },
  { h: 'SYMBOL', title: 'Stock symbol. Coloured dot = direction (● green=bullish, ● red=bearish)' },
  { h: 'TYPE',   title: 'Signal type — hover each badge for a full description' },
  { h: 'PRICE',  title: 'Price at the moment the signal triggered' },
  { h: 'VOL',    title: 'Volume ratio vs 20-day average (2× = twice normal volume — institutional interest)' },
  { h: 'MTF',    title: 'Multi-timeframe bias — 15m and 1h trend alignment. Aligned bias = higher-conviction signal' },
  { h: 'LEVELS', title: 'Trade levels: E=Entry zone, SL=Stop Loss, T1=Target 1' },
  { h: 'ADV',    title: 'Avg Daily Value traded (20-day, ₹Cr) — liquidity gauge. Use VALUE filter to screen by size.' },
  { h: 'CHG%',   title: "Today's price change from yesterday's close" },
  { h: '52H%',   title: '% below 52-week high (0% = at record high; negative = room below highs)' },
  { h: 'SCORE',  title: 'Signal composite score — momentum + volume + structure quality (higher = stronger setup)' },
  { h: 'NOTE',   title: 'Your private trading notes for this signal' },
];

export const SignalFeed = memo(({
  signals, metricsCache, notes, onSaveNote, category, minAdvCr, viewMode, emptyLabel,
  hasMore, onLoadMore,
}: SignalFeedProps) => {
  const [noteModalId, setNoteModalId] = useState<string | null>(null);

  const filtered = useMemo(
    () => filterSignals(signals, category, minAdvCr, metricsCache),
    [signals, category, minAdvCr, metricsCache],
  );
  const openNote = useCallback((id: string) => setNoteModalId(id), []);
  const [chartSymbol, setChartSymbol] = useState<string | null>(null);
  const [ocSymbol, setOcSymbol] = useState<string | null>(null);
  const openChart = useCallback((sym: string) => setChartSymbol(sym), []);
  const openOC = useCallback((sym: string) => setOcSymbol(sym), []);

  const tableParentRef = useRef<HTMLDivElement>(null);
  const tableVirtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => tableParentRef.current,
    estimateSize: () => 34,
    overscan: 15,
  });

  const handleTableScroll = useCallback(() => {
    const el = tableParentRef.current;
    if (!el || !hasMore || !onLoadMore) return;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 200) {
      onLoadMore();
    }
  }, [hasMore, onLoadMore]);

  const cardParentRef = useRef<HTMLDivElement>(null);
  const handleCardScroll = useCallback(() => {
    const el = cardParentRef.current;
    if (!el || !hasMore || !onLoadMore) return;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 400) {
      onLoadMore();
    }
  }, [hasMore, onLoadMore]);

  if (filtered.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-xs gap-2" style={{ color: '#2a3f58' }}>
        <span>{emptyLabel ?? 'No signals'}</span>
      </div>
    );
  }

  if (viewMode === 'table') {
    const tvItems = tableVirtualizer.getVirtualItems();
    const tvTotal = tableVirtualizer.getTotalSize();
    return (
      <>
        <LatestSignalsBar signals={filtered.slice(0, 3)} metricsCache={metricsCache} onChart={openChart} />
        <div ref={tableParentRef} className="flex-1 overflow-auto" onScroll={handleTableScroll}>
        <table className="w-full text-[11px] border-collapse">
          <thead className="sticky top-0 bg-panel z-10">
            <tr className="border-b border-border">
              {TABLE_HEADERS.map(({ h, title }) => (
                <th key={h} title={title} className="px-3 py-2 text-left font-bold text-[9px] tracking-[0.14em] whitespace-nowrap select-none uppercase" style={{ color: '#2a3f58' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tvItems.length > 0 && (
              <tr><td colSpan={TABLE_HEADERS.length} style={{ height: tvItems[0].start, padding: 0, border: 'none' }} /></tr>
            )}
            {tvItems.map(vi => (
              <SignalRow
                key={filtered[vi.index].id}
                signal={filtered[vi.index]}
                metrics={metricsCache[filtered[vi.index].symbol]}
                note={notes[filtered[vi.index].id]}
                onNoteClick={openNote}
                onChart={openChart}
                onOptionChain={openOC}
              />
            ))}
            {tvItems.length > 0 && (
              <tr><td colSpan={TABLE_HEADERS.length} style={{ height: tvTotal - tvItems[tvItems.length - 1].end, padding: 0, border: 'none' }} /></tr>
            )}
          </tbody>
        </table>
        </div>

        {noteModalId && (
          <NoteModal
            id={noteModalId}
            note={notes[noteModalId]}
            onSave={onSaveNote}
            onClose={() => setNoteModalId(null)}
          />
        )}

        {/* Chart modal */}
        {chartSymbol && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
               onClick={() => setChartSymbol(null)}
               onKeyDown={e => { if (e.key === 'Escape') setChartSymbol(null); }}
               tabIndex={-1}>
            <div className="bg-panel border border-border/80 rounded-lg shadow-2xl overflow-hidden"
                 style={{ width: 900, maxWidth: '95vw' }}
                 onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between px-4 py-2 border-b border-border/50">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-fg">{chartSymbol}</span>
                  {metricsCache[chartSymbol]?.is_fno && (
                    <span className="text-[7px] font-black px-1 py-0.5 rounded-sm"
                          style={{ background: '#9b72f718', color: '#9b72f7' }}>F&amp;O</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {metricsCache[chartSymbol]?.is_fno && (
                    <button onClick={() => { setChartSymbol(null); setOcSymbol(chartSymbol); }}
                      className="text-[10px] font-bold text-accent hover:text-fg transition-colors px-2 py-1 border border-accent/40 rounded-sm">OC</button>
                  )}
                  <button onClick={() => setChartSymbol(null)}
                    className="text-ghost hover:text-fg transition-colors text-base leading-none px-1">✕</button>
                </div>
              </div>
              <DailyChart symbol={chartSymbol} height={420} />
            </div>
          </div>
        )}

        {/* Option chain modal */}
        {ocSymbol && (
          <OptionChainPanel symbol={ocSymbol} onClose={() => setOcSymbol(null)} scoreData={null} />
        )}
      </>
    );
  }

  return (
    <>
      <LatestSignalsBar signals={filtered.slice(0, 3)} metricsCache={metricsCache} onChart={openChart} />
      <div ref={cardParentRef} className="flex-1 overflow-y-auto p-3 relative" onScroll={handleCardScroll}>
        <div className="signal-grid">
          {filtered.map(s => (
            <SignalCard
              key={s.id}
              signal={s}
              metrics={metricsCache[s.symbol]}
              note={notes[s.id]}
              onSave={onSaveNote}
              onChart={openChart}
              onOptionChain={openOC}
            />
          ))}
        </div>

        {/* Chart modal */}
        {chartSymbol && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
               onClick={() => setChartSymbol(null)}
               onKeyDown={e => { if (e.key === 'Escape') setChartSymbol(null); }}
               tabIndex={-1}>
            <div className="bg-panel border border-border/80 rounded-lg shadow-2xl overflow-hidden"
                 style={{ width: 900, maxWidth: '95vw' }}
                 onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between px-4 py-2 border-b border-border/50">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-fg">{chartSymbol}</span>
                  {metricsCache[chartSymbol]?.is_fno && (
                    <span className="text-[7px] font-black px-1 py-0.5 rounded-sm"
                          style={{ background: '#9b72f718', color: '#9b72f7' }}>F&amp;O</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {metricsCache[chartSymbol]?.is_fno && (
                    <button onClick={() => { setChartSymbol(null); setOcSymbol(chartSymbol); }}
                      className="text-[10px] font-bold text-accent hover:text-fg transition-colors px-2 py-1 border border-accent/40 rounded-sm">OC</button>
                  )}
                  <button onClick={() => setChartSymbol(null)}
                    className="text-ghost hover:text-fg transition-colors text-base leading-none px-1">✕</button>
                </div>
              </div>
              <DailyChart symbol={chartSymbol} height={420} />
            </div>
          </div>
        )}

        {/* Option chain modal */}
        {ocSymbol && (
          <OptionChainPanel symbol={ocSymbol} onClose={() => setOcSymbol(null)} scoreData={null} />
        )}
      </div>
    </>
  );
});

SignalFeed.displayName = 'SignalFeed';
