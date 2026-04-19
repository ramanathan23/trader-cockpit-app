'use client';

import { memo, useCallback, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { ScreenerRow } from '@/domain/screener';
import { advColor } from '@/domain/signal';
import { fmt2, fmtAdv } from '@/lib/fmt';

interface ScreenerTableProps {
  rows: ScreenerRow[];
  sortCol: string;
  sortAsc: boolean;
  onSort: (col: string) => void;
  loading: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  onChart?: (sym: string) => void;
  onOptionChain?: (sym: string) => void;
}

const COLS: { key: string; label: string; title?: string; align?: 'left' | 'right' }[] = [
  { key: 'symbol', label: 'Symbol', align: 'left' },
  { key: 'adv_20_cr', label: 'ADV' },
  { key: 'atr_14', label: 'ATR' },
  { key: 'display_price', label: 'Price', title: 'Live price when available, otherwise previous close' },
  { key: 'dvwap_delta_pct', label: 'DVWAP%', title: 'Percent above or below session VWAP' },
  { key: 'ema50_delta_pct', label: '50E%', title: 'Percent above or below 50-day EMA' },
  { key: 'ema200_delta_pct', label: '200E%', title: 'Percent above or below 200-day EMA' },
  { key: 'f52h', label: '52H%', title: 'Distance from 52-week high' },
  { key: 'f52l', label: '52L%', title: 'Distance from 52-week low' },
  { key: 'week_return_pct', label: 'WK%', title: 'Five-session return' },
  { key: 'week_gain_pct', label: 'W+%', title: 'Percent above rolling five-session low' },
  { key: 'week_decline_pct', label: 'W-%', title: 'Percent below rolling five-session high' },
];

function pctColor(value?: number | null, invert = false): string {
  if (value == null) return 'rgb(var(--ghost))';
  const score = invert ? -value : value;
  if (score >= 2) return 'rgb(var(--bull))';
  if (score >= 0) return 'rgb(var(--fg))';
  if (score >= -3) return 'rgb(var(--amber))';
  return 'rgb(var(--bear))';
}

function pctText(value?: number | null, forcePlus = false): string {
  if (value == null) return '-';
  const prefix = value > 0 || (forcePlus && value >= 0) ? '+' : '';
  return `${prefix}${value.toFixed(1)}%`;
}

export const ScreenerTable = memo(({ rows, sortCol, sortAsc, onSort, loading, hasMore, onLoadMore, onChart, onOptionChain }: ScreenerTableProps) => {
  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 38,
    overscan: 20,
  });

  const handleScroll = useCallback(() => {
    const el = parentRef.current;
    if (!el || loading || !hasMore || !onLoadMore) return;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 220) onLoadMore();
  }, [loading, hasMore, onLoadMore]);

  if (loading && rows.length === 0) {
    return <div className="flex flex-1 items-center justify-center text-[13px] text-dim">Loading metrics</div>;
  }

  if (rows.length === 0) {
    return <div className="flex flex-1 items-center justify-center text-[13px] text-dim">No data matches the active filters.</div>;
  }

  const items = rowVirtualizer.getVirtualItems();
  const total = rowVirtualizer.getTotalSize();

  return (
    <div ref={parentRef} className="table-wrap flex-1" onScroll={handleScroll}>
      <table className="data-table">
        <thead>
          <tr>
            <th colSpan={4} className="border-r border-border/50 text-left">Price data</th>
            <th colSpan={3} className="border-r border-border/50 text-left">Indicators</th>
            <th colSpan={5} className="text-left">52-week and momentum</th>
          </tr>
          <tr>
            {COLS.map(col => (
              <th
                key={col.key}
                title={col.title}
                onClick={() => onSort(col.key)}
                className={`${col.align === 'left' ? 'text-left' : 'text-right'} cursor-pointer hover:text-fg`}
                style={{ color: sortCol === col.key ? 'rgb(var(--accent))' : undefined }}
              >
                {col.label}{sortCol === col.key ? (sortAsc ? ' ^' : ' v') : ''}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.length > 0 && (
            <tr><td colSpan={COLS.length} style={{ height: items[0].start, padding: 0, border: 'none' }} /></tr>
          )}
          {items.map(item => (
            <ScreenerTableRow key={rows[item.index].symbol} row={rows[item.index]} onChart={onChart} onOptionChain={onOptionChain} />
          ))}
          {items.length > 0 && (
            <tr><td colSpan={COLS.length} style={{ height: total - items[items.length - 1].end, padding: 0, border: 'none' }} /></tr>
          )}
        </tbody>
      </table>
    </div>
  );
});
ScreenerTable.displayName = 'ScreenerTable';

const ScreenerTableRow = memo(({ row: r, onChart }: {
  row: ScreenerRow;
  onChart?: (sym: string) => void;
  onOptionChain?: (sym: string) => void;
}) => {
  const f52hColor =
    r.f52h == null ? 'rgb(var(--ghost))' :
    r.f52h >= -2 ? 'rgb(var(--bull))' :
    r.f52h >= -10 ? 'rgb(var(--amber))' : 'rgb(var(--bear))';

  const f52lColor =
    r.f52l == null ? 'rgb(var(--ghost))' :
    r.f52l > 50 ? 'rgb(var(--bull))' :
    r.f52l > 20 ? 'rgb(var(--amber))' :
    r.f52l > 5 ? 'rgb(var(--fg))' : 'rgb(var(--bear))';

  return (
    <tr className="cursor-pointer" onClick={() => onChart?.(r.symbol)}>
      <td className="text-left text-ticker text-fg">{r.symbol}</td>
      <td className="text-right"><span className="num font-bold" style={{ color: r.adv_20_cr != null ? advColor(r.adv_20_cr) : 'rgb(var(--ghost))' }}>{fmtAdv(r.adv_20_cr)}</span></td>
      <td className="text-right"><span className="num font-bold" style={{ color: 'rgb(var(--amber))' }}>{r.atr_14 != null ? r.atr_14.toFixed(2) : '-'}</span></td>
      <td className="text-right"><span className="num text-[13px] font-black text-fg">{fmt2(r.display_price)}</span></td>
      <td className="text-right"><span className="num font-bold" style={{ color: pctColor(r.dvwap_delta_pct) }}>{pctText(r.dvwap_delta_pct, true)}</span></td>
      <td className="text-right"><span className="num font-bold" style={{ color: pctColor(r.ema50_delta_pct) }}>{pctText(r.ema50_delta_pct, true)}</span></td>
      <td className="text-right"><span className="num font-bold" style={{ color: pctColor(r.ema200_delta_pct) }}>{pctText(r.ema200_delta_pct, true)}</span></td>
      <td className="text-right"><span className="num font-bold" style={{ color: f52hColor }}>{pctText(r.f52h)}</span></td>
      <td className="text-right"><span className="num font-bold" style={{ color: f52lColor }}>{r.f52l != null ? `+${r.f52l.toFixed(1)}%` : '-'}</span></td>
      <td className="text-right"><span className="num font-bold" style={{ color: pctColor(r.week_return_pct) }}>{pctText(r.week_return_pct, true)}</span></td>
      <td className="text-right"><span className="num font-bold" style={{ color: pctColor(r.week_gain_pct, true) }}>{pctText(r.week_gain_pct, true)}</span></td>
      <td className="text-right"><span className="num font-bold" style={{ color: pctColor(r.week_decline_pct, true) }}>{pctText(r.week_decline_pct)}</span></td>
    </tr>
  );
});
ScreenerTableRow.displayName = 'ScreenerTableRow';
