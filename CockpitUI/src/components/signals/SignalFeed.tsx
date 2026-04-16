'use client';

import { memo, useCallback, useMemo, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { filterSignals, type Signal, type SignalCategory } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { SignalCard } from './SignalCard';
import { SignalRow } from './SignalRow';

interface SignalFeedProps {
  signals: Signal[];
  metricsCache: Record<string, InstrumentMetrics | null>;
  notes: Record<string, string>;
  onSaveNote: (id: string, text: string) => void;
  category: SignalCategory;
  minAdvCr: number;
  viewMode: 'card' | 'table';
  emptyLabel?: string;
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
}: SignalFeedProps) => {
  const [noteModalId, setNoteModalId] = useState<string | null>(null);

  const filtered = useMemo(
    () => filterSignals(signals, category, minAdvCr, metricsCache),
    [signals, category, minAdvCr, metricsCache],
  );
  const openNote = useCallback((id: string) => setNoteModalId(id), []);

  const tableParentRef = useRef<HTMLDivElement>(null);
  const tableVirtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => tableParentRef.current,
    estimateSize: () => 34,
    overscan: 15,
  });

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
      <div ref={tableParentRef} className="flex-1 overflow-auto">
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
              />
            ))}
            {tvItems.length > 0 && (
              <tr><td colSpan={TABLE_HEADERS.length} style={{ height: tvTotal - tvItems[tvItems.length - 1].end, padding: 0, border: 'none' }} /></tr>
            )}
          </tbody>
        </table>

        {noteModalId && (
          <NoteModal
            id={noteModalId}
            note={notes[noteModalId]}
            onSave={onSaveNote}
            onClose={() => setNoteModalId(null)}
          />
        )}
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-3">
      <div className="signal-grid">
        {filtered.map(s => (
          <SignalCard
            key={s.id}
            signal={s}
            metrics={metricsCache[s.symbol]}
            note={notes[s.id]}
            onSave={onSaveNote}
          />
        ))}
      </div>
    </div>
  );
});

SignalFeed.displayName = 'SignalFeed';
