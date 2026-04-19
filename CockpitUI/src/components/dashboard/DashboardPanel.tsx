'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useDashboard } from '@/hooks/useDashboard';
import { DailyChart } from './DailyChart';
import { OptionChainPanel } from './OptionChainPanel';
import { fmt2, fmtAdv } from '@/lib/fmt';
import type { ScoredSymbol } from '@/domain/dashboard';

type SortKey =
  | 'rank'
  | 'total_score'
  | 'momentum_score'
  | 'trend_score'
  | 'volatility_score'
  | 'structure_score'
  | 'adx_14'
  | 'rsi_14'
  | 'adv_20_cr';

type Segment = 'all' | 'fno' | 'equity';

interface DashboardPanelProps {
  active: boolean;
}

const HEADERS: { key: string; label: string; title: string; align: 'left' | 'right' | 'center'; sortable: boolean }[] = [
  { key: 'rank', label: '#', title: 'Rank', align: 'center', sortable: true },
  { key: 'symbol', label: 'Symbol', title: 'Symbol and tags', align: 'left', sortable: false },
  { key: 'total_score', label: 'Total', title: 'Unified score', align: 'right', sortable: true },
  { key: 'momentum_score', label: 'Mom', title: 'Momentum score', align: 'right', sortable: true },
  { key: 'trend_score', label: 'Trend', title: 'Trend score', align: 'right', sortable: true },
  { key: 'volatility_score', label: 'Vol', title: 'Volatility score', align: 'right', sortable: true },
  { key: 'structure_score', label: 'Struct', title: 'Structure score', align: 'right', sortable: true },
  { key: 'adx_14', label: 'ADX', title: 'ADX(14)', align: 'right', sortable: true },
  { key: 'rsi_14', label: 'RSI', title: 'RSI(14)', align: 'right', sortable: true },
  { key: 'adv_20_cr', label: 'ADV', title: 'Average daily value', align: 'right', sortable: true },
  { key: 'weekly', label: 'W', title: 'Weekly bias', align: 'center', sortable: false },
  { key: 'close', label: 'Close', title: 'Previous close', align: 'right', sortable: false },
  { key: 'oc', label: 'OC', title: 'Option chain', align: 'center', sortable: false },
];

export function DashboardPanel({ active }: DashboardPanelProps) {
  const { stats, scores, loading, fetched, loadDashboard } = useDashboard();
  const [watchlistOnly, setWatchlistOnly] = useState(false);
  const [segment, setSegment] = useState<Segment>('all');
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('total_score');
  const [sortAsc, setSortAsc] = useState(false);
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);
  const [ocSymbol, setOcSymbol] = useState<string | null>(null);

  useEffect(() => {
    if (active && !fetched && !loading) loadDashboard({ watchlistOnly });
  }, [active]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (fetched) loadDashboard({ watchlistOnly });
  }, [watchlistOnly]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (segment === 'all') {
      setSortKey('total_score');
      setSortAsc(false);
    } else {
      setSortKey('rank');
      setSortAsc(true);
    }
  }, [segment]);

  const filtered = useMemo(() => {
    const q = query.trim().toUpperCase();
    let rows = scores;
    if (segment === 'fno') rows = rows.filter(row => row.is_fno === true);
    if (segment === 'equity') rows = rows.filter(row => row.is_fno !== true);
    if (q) rows = rows.filter(row => row.symbol.includes(q) || row.company_name?.toUpperCase().includes(q));

    return [...rows].sort((a, b) => {
      const av = a[sortKey] ?? 0;
      const bv = b[sortKey] ?? 0;
      return sortAsc ? Number(av) - Number(bv) : Number(bv) - Number(av);
    });
  }, [scores, segment, query, sortKey, sortAsc]);

  const handleSort = useCallback((key: SortKey) => {
    setSortAsc(prev => sortKey === key ? !prev : key === 'rank');
    setSortKey(key);
  }, [sortKey]);

  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: index => expandedSymbol === filtered[index]?.symbol ? 324 : 44,
    overscan: 12,
  });

  const virtualItems = rowVirtualizer.getVirtualItems();
  const totalSize = rowVirtualizer.getTotalSize();

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="border-b border-border bg-panel/72 px-4 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder="Search symbol"
            className="field w-44 text-[12px]"
            style={{ colorScheme: 'inherit' }}
          />

          <div className="seg-group">
            <button type="button" onClick={() => setWatchlistOnly(false)} className={`seg-btn ${!watchlistOnly ? 'active' : ''}`}>All</button>
            <button type="button" onClick={() => setWatchlistOnly(true)} className={`seg-btn ${watchlistOnly ? 'active' : ''}`} style={watchlistOnly ? { color: 'rgb(var(--amber))' } : undefined}>Watchlist</button>
          </div>

          <div className="seg-group">
            {(['all', 'fno', 'equity'] as Segment[]).map(item => (
              <button
                key={item}
                type="button"
                onClick={() => setSegment(item)}
                className={`seg-btn ${segment === item ? 'active' : ''}`}
                style={segment === item && item === 'fno' ? { color: 'rgb(var(--violet))' } : segment === item && item === 'equity' ? { color: 'rgb(var(--bull))' } : undefined}
              >
                {item === 'fno' ? 'F&O' : item === 'equity' ? 'Equity' : 'All'}
              </button>
            ))}
          </div>

          <div className="ml-auto flex items-center gap-2">
            <button
              type="button"
              onClick={() => loadDashboard({ watchlistOnly })}
              disabled={loading}
              className="icon-btn"
              title="Refresh dashboard"
              aria-label="Refresh dashboard"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M20 12a8 8 0 0 1-13.7 5.7M4 12A8 8 0 0 1 17.7 6.3M18 3v4h-4M6 21v-4h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </div>

        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          <StatCard label="Score date" value={stats.score_date || '-'} />
          <StatCard label="Scored" value={stats.total_scored} />
          <StatCard label="Average" value={stats.avg_score} />
          <StatCard label="High conviction" value={stats.high_conviction} tone="bull" />
          <StatCard label="Above avg" value={stats.above_average} tone="accent" />
        </div>
      </div>

      <div ref={parentRef} className="table-wrap flex-1">
        <table className="data-table">
          <thead>
            <tr>
              {HEADERS.map(header => (
                <th
                  key={header.key}
                  title={header.title}
                  onClick={() => header.sortable && handleSort(header.key as SortKey)}
                  className={`${header.align === 'right' ? 'text-right' : header.align === 'center' ? 'text-center' : 'text-left'} ${header.sortable ? 'cursor-pointer hover:text-fg' : ''}`}
                  style={{ color: sortKey === header.key ? 'rgb(var(--accent))' : undefined }}
                >
                  {header.label}{sortKey === header.key ? (sortAsc ? ' ^' : ' v') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {virtualItems.length > 0 && (
              <tr><td colSpan={HEADERS.length} style={{ height: virtualItems[0].start, padding: 0, border: 'none' }} /></tr>
            )}
            {virtualItems.map(item => {
              const row = filtered[item.index];
              return (
                <ScoreRow
                  key={row.symbol}
                  row={row}
                  expanded={expandedSymbol === row.symbol}
                  onToggle={symbol => setExpandedSymbol(prev => prev === symbol ? null : symbol)}
                  onOptionChain={setOcSymbol}
                />
              );
            })}
            {virtualItems.length > 0 && (
              <tr><td colSpan={HEADERS.length} style={{ height: totalSize - virtualItems[virtualItems.length - 1].end, padding: 0, border: 'none' }} /></tr>
            )}
          </tbody>
        </table>

        {filtered.length === 0 && !loading && (
          <div className="flex h-48 items-center justify-center text-[13px] text-dim">
            {scores.length === 0 ? 'No scores yet. Run compute to build the dashboard.' : 'No symbols match the active filters.'}
          </div>
        )}
      </div>

      <div className="flex shrink-0 items-center justify-between border-t border-border bg-panel/80 px-4 py-2 text-[11px] text-ghost">
        <span className="num">{filtered.length}/{scores.length} symbols</span>
        <span className="flex gap-3">
          <span style={{ color: 'rgb(var(--violet))' }}>F&O {scores.filter(row => row.is_fno === true).length}</span>
          <span style={{ color: 'rgb(var(--bull))' }}>Equity {scores.filter(row => row.is_fno !== true).length}</span>
        </span>
      </div>

      {ocSymbol && <OptionChainPanel symbol={ocSymbol} onClose={() => setOcSymbol(null)} />}
    </div>
  );
}

function StatCard({ label, value, tone }: { label: string; value: string | number; tone?: 'bull' | 'accent' }) {
  const color = tone === 'bull' ? 'rgb(var(--bull))' : tone === 'accent' ? 'rgb(var(--accent))' : 'rgb(var(--fg))';
  return (
    <div className="metric-card">
      <div className="text-[10px] font-black uppercase text-ghost">{label}</div>
      <div className="num mt-1 truncate text-[19px] font-black" style={{ color }}>{value}</div>
    </div>
  );
}

function ScoreRow({
  row,
  expanded,
  onToggle,
  onOptionChain,
}: {
  row: ScoredSymbol;
  expanded: boolean;
  onToggle: (sym: string) => void;
  onOptionChain: (sym: string) => void;
}) {
  return (
    <>
      <tr className={`group cursor-pointer ${expanded ? 'bg-lift' : ''}`} onClick={() => onToggle(row.symbol)}>
        <td className="text-center num text-dim">{row.rank}</td>
        <td className="whitespace-nowrap">
          <div className="flex items-center gap-2">
            <span className="text-ticker text-fg">{row.symbol}</span>
            {row.is_fno && <span className="chip h-5 min-h-0 px-1.5" style={{ color: 'rgb(var(--violet))' }}>F&O</span>}
            {row.is_watchlist && <span className="chip h-5 min-h-0 px-1.5" style={{ color: 'rgb(var(--amber))' }}>WL</span>}
            {row.bb_squeeze && <span className="chip h-5 min-h-0 px-1.5" style={{ color: 'rgb(var(--violet))' }}>SQ{row.squeeze_days}</span>}
            {row.nr7 && <span className="chip h-5 min-h-0 px-1.5" style={{ color: 'rgb(var(--sky))' }}>NR7</span>}
          </div>
          {row.company_name && <div className="max-w-[220px] truncate text-[10px] text-ghost">{row.company_name}</div>}
        </td>
        <td className="text-right"><ScoreBar value={row.total_score} color="rgb(var(--accent))" /></td>
        <td className="text-right"><ScoreBar value={row.momentum_score} color="rgb(var(--amber))" /></td>
        <td className="text-right"><ScoreBar value={row.trend_score} color="rgb(var(--bull))" /></td>
        <td className="text-right"><ScoreBar value={row.volatility_score} color="rgb(var(--violet))" /></td>
        <td className="text-right"><ScoreBar value={row.structure_score} color="rgb(var(--sky))" /></td>
        <td className="text-right num text-dim">{row.adx_14 != null ? row.adx_14.toFixed(0) : '-'}</td>
        <td className="text-right num font-bold" style={{ color: rsiColor(row.rsi_14) }}>{row.rsi_14 != null ? row.rsi_14.toFixed(0) : '-'}</td>
        <td className="text-right num text-dim">{fmtAdv(row.adv_20_cr)}</td>
        <td className="text-center font-black" style={{ color: row.weekly_bias === 'BULLISH' ? 'rgb(var(--bull))' : row.weekly_bias === 'BEARISH' ? 'rgb(var(--bear))' : 'rgb(var(--ghost))' }}>
          {row.weekly_bias === 'BULLISH' ? 'UP' : row.weekly_bias === 'BEARISH' ? 'DN' : '-'}
        </td>
        <td className="text-right num text-dim">{fmt2(row.prev_day_close)}</td>
        <td className="text-center">
          <button
            type="button"
            onClick={event => {
              event.stopPropagation();
              onOptionChain(row.symbol);
            }}
            className="text-[10px] font-black text-accent opacity-0 transition-opacity group-hover:opacity-100"
            title="View option chain"
          >
            OC
          </button>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={HEADERS.length} className="bg-base p-0">
            <DailyChart symbol={row.symbol} height={280} />
          </td>
        </tr>
      )}
    </>
  );
}

function ScoreBar({ value, color }: { value: number; color: string }) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div className="flex items-center justify-end gap-2">
      <span className="num text-[11px] font-black" style={{ color }}>{value.toFixed(0)}</span>
      <div className="h-1.5 w-[54px] overflow-hidden rounded-full bg-border">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function rsiColor(v: number | null | undefined): string {
  if (v == null) return 'rgb(var(--ghost))';
  if (v >= 70) return 'rgb(var(--bear))';
  if (v <= 30) return 'rgb(var(--bull))';
  return 'rgb(var(--amber))';
}
