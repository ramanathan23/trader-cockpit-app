'use client';

import { memo, useCallback, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { ScreenerRow } from '@/domain/screener';
import { advColor } from '@/domain/signal';
import { fmt2, fmtAdv } from '@/lib/fmt';

interface ScreenerTableProps {
  rows:       ScreenerRow[];
  sortCol:    string;
  sortAsc:    boolean;
  onSort:     (col: string) => void;
  loading:    boolean;
  hasMore?:   boolean;
  onLoadMore?: () => void;
  onChart?:       (sym: string) => void;
  onOptionChain?: (sym: string) => void;
}

const COL_GROUPS = [
  { label: 'PRICE DATA', cols: ['symbol', 'adv_20_cr', 'atr_14', 'display_price'] },
  { label: 'INDICATORS', cols: ['dvwap_delta_pct', 'ema50_delta_pct', 'ema200_delta_pct'] },
  { label: '52-WEEK & MOMENTUM', cols: ['f52h', 'f52l', 'week_return_pct', 'week_gain_pct', 'week_decline_pct'] },
];

const COLS: { key: string; label: string; title?: string; align?: 'left' | 'right'; group?: string }[] = [
  { key: 'symbol',        label: 'SYMBOL',  align: 'left', group: 'price' },
  { key: 'adv_20_cr',     label: 'ADV', group: 'price' },
  { key: 'atr_14',        label: 'ATR', group: 'price' },
  { key: 'display_price', label: 'PRICE', title: 'Live price when available, otherwise previous close', group: 'price' },
  { key: 'dvwap_delta_pct', label: 'DVWAP%', title: '% above or below the current session VWAP', group: 'indicators' },
  { key: 'ema50_delta_pct', label: '50E%', title: '% above or below the 50-day EMA', group: 'indicators' },
  { key: 'ema200_delta_pct', label: '200E%', title: '% above or below the 200-day EMA', group: 'indicators' },
  { key: 'f52h',          label: '52H%',   title: '% below 52-week high (0 = at high)', group: 'momentum' },
  { key: 'f52l',          label: '52L%',   title: '% above 52-week low', group: 'momentum' },
  { key: 'week_return_pct', label: 'WK%', title: '% return versus 5 trading sessions ago', group: 'momentum' },
  { key: 'week_gain_pct', label: 'W+%', title: '% above the rolling 5-session low', group: 'momentum' },
  { key: 'week_decline_pct', label: 'W-%', title: '% below the rolling 5-session high', group: 'momentum' },
];

const SortArrow = ({ col, sortCol, sortAsc }: { col: string; sortCol: string; sortAsc: boolean }) =>
  sortCol === col ? <span className="ml-0.5">{sortAsc ? '▲' : '▼'}</span> : null;

function pctColor(value?: number | null, invert = false): string {
  if (value == null) return '#5a7796';
  const score = invert ? -value : value;
  if (score >= 2) return '#0dbd7d';
  if (score >= 0) return '#c5d8f0';
  if (score >= -3) return '#e8933a';
  return '#f23d55';
}

function pctText(value?: number | null, forcePlus = false): string {
  if (value == null) return '—';
  const prefix = value > 0 || (forcePlus && value >= 0) ? '+' : '';
  return `${prefix}${value.toFixed(1)}%`;
}

export const ScreenerTable = memo(({ rows, sortCol, sortAsc, onSort, loading, hasMore, onLoadMore, onChart, onOptionChain }: ScreenerTableProps) => {
  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 36,
    overscan: 20,
  });

  const handleScroll = useCallback(() => {
    const el = parentRef.current;
    if (!el || loading || !hasMore || !onLoadMore) return;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 200) {
      onLoadMore();
    }
  }, [loading, hasMore, onLoadMore]);

  if (loading && rows.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-[11px] animate-blink" style={{ color: '#2a3f58' }}>
        Loading metrics…
      </div>
    );
  }
  if (rows.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-40 gap-2" style={{ color: '#2a3f58' }}>
        <span className="text-2xl opacity-30">&#9783;</span>
        <span className="text-xs">No data — adjust filters</span>
      </div>
    );
  }

  const virtualItems = rowVirtualizer.getVirtualItems();
  const totalSize = rowVirtualizer.getTotalSize();

  return (
    <div ref={parentRef} className="flex-1 overflow-auto" onScroll={handleScroll}>
      <table className="w-full text-[11px] border-collapse">
        <thead className="sticky top-0 bg-panel z-10">
          {/* Column group headers */}
          <tr className="border-b border-border/50">
            <th colSpan={4} className="px-2 py-1 text-left text-[8px] font-bold tracking-wider uppercase text-ghost border-r border-border/30">
              PRICE DATA
            </th>
            <th colSpan={3} className="px-2 py-1 text-left text-[8px] font-bold tracking-wider uppercase text-ghost border-r border-border/30">
              INDICATORS
            </th>
            <th colSpan={5} className="px-2 py-1 text-left text-[8px] font-bold tracking-wider uppercase text-ghost">
              52-WEEK & MOMENTUM
            </th>
          </tr>
          <tr className="border-b border-border">
            {COLS.map((c, i) => (
              <th
                key={`${c.key}-${i}`}
                title={c.title}
                onClick={() => onSort(c.key)}
                className={`px-2.5 py-1.5 font-bold text-[9px] tracking-[0.12em] cursor-pointer select-none whitespace-nowrap uppercase transition-colors hover:text-fg ${
                  c.align === 'left' ? 'text-left' : 'text-right'
                }`}
                style={{ color: sortCol === c.key ? '#2d7ee8' : '#5a7796' }}
              >
                {c.label}
                {sortCol === c.key && <span className="ml-0.5">{sortAsc ? '▲' : '▼'}</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {virtualItems.length > 0 && (
            <tr><td colSpan={COLS.length} style={{ height: virtualItems[0].start, padding: 0, border: 'none' }} /></tr>
          )}
          {virtualItems.map(vi => (
            <ScreenerTableRow key={rows[vi.index].symbol} row={rows[vi.index]} onChart={onChart} onOptionChain={onOptionChain} />
          ))}
          {virtualItems.length > 0 && (
            <tr><td colSpan={COLS.length} style={{ height: totalSize - virtualItems[virtualItems.length - 1].end, padding: 0, border: 'none' }} /></tr>
          )}
        </tbody>
      </table>
    </div>
  );
});
ScreenerTable.displayName = 'ScreenerTable';

const ScreenerTableRow = memo(({ row: r, onChart, onOptionChain }: { 
  row: ScreenerRow;
  onChart?: (sym: string) => void;
  onOptionChain?: (sym: string) => void;
}) => {
  const f52hColor =
    r.f52h == null ? '#5a7796' :
    r.f52h >= -2   ? '#0dbd7d' :
    r.f52h >= -10  ? '#e8933a' : '#f23d55';

  const f52lColor =
    r.f52l == null ? '#5a7796' :
    r.f52l > 50    ? '#0dbd7d' :
    r.f52l > 20    ? '#e8933a' :
    r.f52l > 5     ? '#c5d8f0' : '#f23d55';

  return (
    <tr className="border-b border-border hover:bg-lift transition-colors group cursor-pointer"
        style={{ height: '36px' }}
        onClick={() => onChart?.(r.symbol)}>
      <td className="px-2.5 py-1.5 text-ticker text-fg">{r.symbol}</td>
      <td className="px-2.5 py-1.5 text-right tabular-nums text-[10px]"
          style={{ color: r.adv_20_cr != null ? advColor(r.adv_20_cr) : '#5a7796' }}>
        <span className="num">{fmtAdv(r.adv_20_cr)}</span>
      </td>
      <td className="px-2.5 py-1.5 text-right tabular-nums text-[10px]" style={{ color: '#e8933a' }}>
        <span className="num">{r.atr_14 != null ? r.atr_14.toFixed(2) : '—'}</span>
      </td>
      <td className="px-2.5 py-1.5 text-right tabular-nums text-[12px] font-bold text-fg">
        <span className="num">{fmt2(r.display_price)}</span>
      </td>
      <td className="px-2.5 py-1.5 text-right tabular-nums font-bold text-[10px]" style={{ color: pctColor(r.dvwap_delta_pct) }}>
        <span className="num">{pctText(r.dvwap_delta_pct, true)}</span>
      </td>
      <td className="px-2.5 py-1.5 text-right tabular-nums font-bold text-[10px]" style={{ color: pctColor(r.ema50_delta_pct) }}>
        <span className="num">{pctText(r.ema50_delta_pct, true)}</span>
      </td>
      <td className="px-2.5 py-1.5 text-right tabular-nums font-bold text-[10px]" style={{ color: pctColor(r.ema200_delta_pct) }}>
        <span className="num">{pctText(r.ema200_delta_pct, true)}</span>
      </td>
      <td className="px-2.5 py-1.5 text-right tabular-nums font-bold text-[10px]" style={{ color: f52hColor }}>
        <span className="num">{r.f52h != null ? (r.f52h >= 0 ? '+' : '') + r.f52h.toFixed(1) + '%' : '—'}</span>
      </td>
      <td className="px-2.5 py-1.5 text-right tabular-nums font-bold text-[10px]" style={{ color: f52lColor }}>
        <span className="num">{r.f52l != null ? '+' + r.f52l.toFixed(1) + '%' : '—'}</span>
      </td>
      <td className="px-2.5 py-1.5 text-right tabular-nums font-bold text-[10px]" style={{ color: pctColor(r.week_return_pct) }}>
        <span className="num">{pctText(r.week_return_pct, true)}</span>
      </td>
      <td className="px-2.5 py-1.5 text-right tabular-nums font-bold text-[10px]" style={{ color: pctColor(r.week_gain_pct, true) }}>
        <span className="num">{pctText(r.week_gain_pct, true)}</span>
      </td>
      <td className="px-2.5 py-1.5 text-right tabular-nums font-bold text-[10px]" style={{ color: pctColor(r.week_decline_pct, true) }}>
        <span className="num">{pctText(r.week_decline_pct)}</span>
      </td>
    </tr>
  );
});
ScreenerTableRow.displayName = 'ScreenerTableRow';
