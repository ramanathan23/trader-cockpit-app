'use client';

import { memo } from 'react';
import type { ScreenerRow } from '@/domain/screener';
import { advColor } from '@/domain/signal';
import { fmt2, fmtAdv } from '@/lib/fmt';

interface ScreenerTableProps {
  rows:     ScreenerRow[];
  sortCol:  string;
  sortAsc:  boolean;
  onSort:   (col: string) => void;
  loading:  boolean;
}

const COLS: { key: string; label: string; title?: string; align?: 'left' | 'right' }[] = [
  { key: 'symbol',        label: 'SYMBOL',  align: 'left' },
  { key: 'adv_20_cr',     label: 'ADV' },
  { key: 'atr_14',        label: 'ATR' },
  { key: 'display_price', label: 'PRICE', title: 'Live price when available, otherwise previous close' },
  { key: 'dvwap_delta_pct', label: 'DVWAP%', title: '% above or below the current session VWAP' },
  { key: 'ema50_delta_pct', label: '50E%', title: '% above or below the 50-day EMA' },
  { key: 'ema200_delta_pct', label: '200E%', title: '% above or below the 200-day EMA' },
  { key: 'f52h',          label: '52H%',   title: '% below 52-week high (0 = at high)' },
  { key: 'f52l',          label: '52L%',   title: '% above 52-week low' },
  { key: 'week_return_pct', label: 'WK%', title: '% return versus 5 trading sessions ago' },
  { key: 'week_gain_pct', label: 'W+%', title: '% above the rolling 5-session low' },
  { key: 'week_decline_pct', label: 'W-%', title: '% below the rolling 5-session high' },
];

const SortArrow = ({ col, sortCol, sortAsc }: { col: string; sortCol: string; sortAsc: boolean }) =>
  sortCol === col ? <span className="ml-0.5">{sortAsc ? '▲' : '▼'}</span> : null;

function pctColor(value?: number | null, invert = false): string {
  if (value == null) return '#2a3f58';
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

export const ScreenerTable = memo(({ rows, sortCol, sortAsc, onSort, loading }: ScreenerTableProps) => {
  if (loading) {
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

  return (
    <div className="flex-1 overflow-auto">
      <table className="w-full text-[11px] border-collapse">
        <thead className="sticky top-0 bg-panel z-10">
          <tr className="border-b border-border">
            {COLS.map((c, i) => (
              <th
                key={`${c.key}-${i}`}
                title={c.title}
                onClick={() => onSort(c.key)}
                className={`px-3 py-2 font-bold text-[9px] tracking-[0.14em] cursor-pointer select-none whitespace-nowrap uppercase transition-colors hover:text-fg ${
                  c.align === 'left' ? 'text-left' : 'text-right'
                }`}
                style={{ color: sortCol === c.key ? '#c5d8f0' : '#2a3f58' }}
              >
                {c.label}
                {sortCol === c.key && <span className="ml-0.5 text-accent">{sortAsc ? '▲' : '▼'}</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <ScreenerTableRow key={r.symbol} row={r} />
          ))}
        </tbody>
      </table>
    </div>
  );
});
ScreenerTable.displayName = 'ScreenerTable';

const ScreenerTableRow = memo(({ row: r }: { row: ScreenerRow }) => {
  const f52hColor =
    r.f52h == null ? '#2a3f58' :
    r.f52h >= -2   ? '#0dbd7d' :
    r.f52h >= -10  ? '#e8933a' : '#f23d55';

  const f52lColor =
    r.f52l == null ? '#2a3f58' :
    r.f52l > 50    ? '#0dbd7d' :
    r.f52l > 20    ? '#e8933a' :
    r.f52l > 5     ? '#c5d8f0' : '#f23d55';

  return (
    <tr className="border-b border-border hover:bg-lift transition-colors">
      <td className="px-3 py-2 font-bold text-fg tracking-wide">{r.symbol}</td>
      <td className="px-3 py-2 text-right tabular-nums"
          style={{ color: r.adv_20_cr != null ? advColor(r.adv_20_cr) : '#2a3f58' }}>
        <span className="num font-semibold">{fmtAdv(r.adv_20_cr)}</span>
      </td>
      <td className="px-3 py-2 text-right tabular-nums" style={{ color: '#e8933a' }}>
        <span className="num">{r.atr_14 != null ? r.atr_14.toFixed(2) : '—'}</span>
      </td>
      <td className="px-3 py-2 text-right tabular-nums text-fg">
        <span className="num font-semibold">{fmt2(r.display_price)}</span>
      </td>
      <td className="px-3 py-2 text-right tabular-nums font-bold" style={{ color: pctColor(r.dvwap_delta_pct) }}>
        <span className="num">{pctText(r.dvwap_delta_pct, true)}</span>
      </td>
      <td className="px-3 py-2 text-right tabular-nums font-bold" style={{ color: pctColor(r.ema50_delta_pct) }}>
        <span className="num">{pctText(r.ema50_delta_pct, true)}</span>
      </td>
      <td className="px-3 py-2 text-right tabular-nums font-bold" style={{ color: pctColor(r.ema200_delta_pct) }}>
        <span className="num">{pctText(r.ema200_delta_pct, true)}</span>
      </td>
      <td className="px-3 py-2 text-right tabular-nums font-bold" style={{ color: f52hColor }}>
        <span className="num">{r.f52h != null ? (r.f52h >= 0 ? '+' : '') + r.f52h.toFixed(1) + '%' : '—'}</span>
      </td>
      <td className="px-3 py-2 text-right tabular-nums font-bold" style={{ color: f52lColor }}>
        <span className="num">{r.f52l != null ? '+' + r.f52l.toFixed(1) + '%' : '—'}</span>
      </td>
      <td className="px-3 py-2 text-right tabular-nums font-bold" style={{ color: pctColor(r.week_return_pct) }}>
        <span className="num">{pctText(r.week_return_pct, true)}</span>
      </td>
      <td className="px-3 py-2 text-right tabular-nums font-bold" style={{ color: pctColor(r.week_gain_pct, true) }}>
        <span className="num">{pctText(r.week_gain_pct, true)}</span>
      </td>
      <td className="px-3 py-2 text-right tabular-nums font-bold" style={{ color: pctColor(r.week_decline_pct, true) }}>
        <span className="num">{pctText(r.week_decline_pct)}</span>
      </td>
    </tr>
  );
});
ScreenerTableRow.displayName = 'ScreenerTableRow';
