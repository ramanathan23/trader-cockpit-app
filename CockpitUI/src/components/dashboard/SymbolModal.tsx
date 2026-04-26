'use client';

import { memo, useEffect, useState } from 'react';
import { X, Maximize2, Minimize2 } from 'lucide-react';
import { cn } from '@/lib/cn';
import { DailyChart } from './DailyChart';
import { OptionChainPanel } from './OptionChainPanel';
import { SymbolModalDetails } from './SymbolModalDetails';
import type { ScoredSymbol } from '@/domain/dashboard';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { scoreToStockRow, type StockRow } from '@/domain/stocklist';
import type { NoteEntry } from '@/hooks/useNotes';

export type SymbolModalTab = 'details' | 'chart' | 'oc';

interface SymbolModalProps {
  symbol:       string;
  row?:         StockRow;
  initialTab?:  SymbolModalTab;
  onClose:      () => void;
  noteEntries?: NoteEntry[];
  onAddNote?:   (symbol: string, text: string) => void;
  onDeleteNote?: (symbol: string, id: string)  => void;
}

const TABS: { key: SymbolModalTab; label: string }[] = [
  { key: 'details', label: 'Details' },
  { key: 'chart',   label: 'Chart' },
  { key: 'oc',      label: 'Option Chain' },
];

function pctFromReference(price?: number | null, reference?: number | null): number | undefined {
  if (price == null || reference == null || reference === 0) return undefined;
  return (price - reference) / reference * 100;
}

function mergeMetricRow(base: StockRow, metric?: InstrumentMetrics): StockRow {
  if (!metric) return base;
  const displayPrice = metric.current_price ?? metric.day_close ?? base.display_price ?? base.prev_day_close;
  return {
    ...base,
    is_fno:         base.is_fno ?? metric.is_fno,
    current_price:  metric.current_price ?? base.current_price,
    display_price:  displayPrice ?? undefined,
    prev_day_high:  metric.prev_day_high ?? base.prev_day_high,
    prev_day_low:   metric.prev_day_low ?? base.prev_day_low,
    prev_day_close: metric.prev_day_close ?? base.prev_day_close,
    week52_high:    metric.week52_high ?? base.week52_high,
    week52_low:     metric.week52_low ?? base.week52_low,
    f52h:           base.f52h ?? pctFromReference(displayPrice, metric.week52_high),
    f52l:           base.f52l ?? pctFromReference(displayPrice, metric.week52_low),
    atr_14:         metric.atr_14 ?? base.atr_14,
    adv_20_cr:      metric.adv_20_cr ?? base.adv_20_cr,
    stage:          base.stage ?? metric.stage ?? undefined,
  };
}

export const SymbolModal = memo(({
  symbol, row, initialTab = 'chart', onClose,
  noteEntries = [], onAddNote, onDeleteNote,
}: SymbolModalProps) => {
  const [tab,      setTab]      = useState<SymbolModalTab>(initialTab);
  const [expanded, setExpanded] = useState(false);
  const [fetchedRow, setFetchedRow] = useState<StockRow | undefined>();
  const detailRow = row ?? fetchedRow;

  useEffect(() => {
    if (row) {
      setFetchedRow(undefined);
      return;
    }

    let active = true;
    const load = async () => {
      try {
        const [dashRes, metricsRes] = await Promise.allSettled([
          fetch(`/scorer/dashboard?limit=2000&_ts=${Date.now()}`).then(r => r.ok ? r.json() : null),
          fetch('/api/v1/instruments/metrics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbols: [symbol] }),
          }).then(r => r.ok ? r.json() : null),
        ]);
        if (!active) return;

        const dash = dashRes.status === 'fulfilled' ? dashRes.value : null;
        const metricMap = metricsRes.status === 'fulfilled' ? metricsRes.value as Record<string, InstrumentMetrics> | null : null;
        const score = (dash?.scores ?? []).find((item: ScoredSymbol) => item.symbol === symbol) as ScoredSymbol | undefined;
        const base = score ? scoreToStockRow(score) : ({ symbol } as StockRow);
        setFetchedRow(mergeMetricRow(base, metricMap?.[symbol]));
      } catch {
        if (active) setFetchedRow({ symbol } as StockRow);
      }
    };

    load();
    return () => { active = false; };
  }, [row, symbol]);

  return (
    <div
      className="modal-backdrop"
      tabIndex={-1}
      onKeyDown={e => { if (e.key === 'Escape') onClose(); }}
    >
      <div
        className="surface-card flex flex-col overflow-hidden transition-all duration-200"
        style={expanded ? { width: '100vw', height: '100vh' } : { width: '82vw', height: '82vh' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-4">
            <span className="text-[15px] font-black text-fg">{symbol}</span>
            {row?.company_name && (
              <span className="max-w-[200px] truncate text-[11px] text-ghost">{row.company_name}</span>
            )}
            <div className="seg-group">
              {TABS.map(t => (
                <button key={t.key} type="button"
                  className={cn('seg-btn', tab === t.key && 'active')}
                  onClick={() => setTab(t.key)}>
                  {t.label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button type="button" className="icon-btn h-8 w-8"
              title={expanded ? 'Restore' : 'Expand'}
              onClick={() => setExpanded(e => !e)}>
              {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
            <button type="button" className="icon-btn h-8 w-8" title="Close" onClick={onClose}>
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className={cn('flex-1 overflow-y-auto p-5', tab !== 'details' && 'hidden')}>
            <SymbolModalDetails
              symbol={symbol} row={detailRow}
              entries={noteEntries}
              onAdd={onAddNote} onDelete={onDeleteNote}
            />
          </div>
          <div className={cn('flex-1 overflow-hidden', tab !== 'chart' && 'hidden')}>
            <DailyChart symbol={symbol} height="100%" />
          </div>
          <div className={cn('flex flex-1 flex-col overflow-hidden', tab !== 'oc' && 'hidden')}>
            <OptionChainPanel symbol={symbol} onClose={onClose} embedded />
          </div>
        </div>
      </div>
    </div>
  );
});
SymbolModal.displayName = 'SymbolModal';
