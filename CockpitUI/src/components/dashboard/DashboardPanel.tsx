'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { BarChart2, ChevronDown, ChevronUp, ChevronsUpDown, Crosshair, LayoutGrid, List, RotateCcw } from 'lucide-react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useDashboard } from '@/hooks/useDashboard';
import { ClusterChart } from './ClusterChart';
import { WatchlistSplitView } from './WatchlistSplitView';
import { SymbolModal } from './SymbolModal';
import type { SymbolModalTab } from './SymbolModal';
import { fmt2, fmtAdv } from '@/lib/fmt';
import type { DashboardResponse, ScoredSymbol } from '@/domain/dashboard';

type SortKey =
  | 'rank'
  | 'total_score'
  | 'momentum_score'
  | 'trend_score'
  | 'volatility_score'
  | 'structure_score'
  | 'adx_14'
  | 'rsi_14'
  | 'adv_20_cr'
  | 'comfort_score';

type Segment = 'all' | 'fno' | 'equity';
type BiasFilter = 'all' | 'bull' | 'bear' | 'neutral';

interface DashboardPanelProps {
  active: boolean;
  initialData?: DashboardResponse | null;
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
  { key: 'comfort_score', label: 'Comfort', title: 'Comfort score (hold ease)', align: 'right', sortable: true },
  { key: 'oc', label: 'OC', title: 'Option chain', align: 'center', sortable: false },
];

export function DashboardPanel({ active, initialData }: DashboardPanelProps) {
  const { stats, scores, loading, fetched, loadDashboard } = useDashboard(initialData);
  const [watchlistOnly, setWatchlistOnly] = useState(false);
  const [viewMode, setViewMode] = useState<'card' | 'table' | 'cluster' | 'charts'>('table');
  const [segment, setSegment] = useState<Segment>('all');
  const [biasFilter, setBiasFilter] = useState<BiasFilter>('all');
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('total_score');
  const [sortAsc, setSortAsc] = useState(false);
  const [detailSymbol, setDetailSymbol] = useState<string | null>(null);
  const [detailTab, setDetailTab] = useState<SymbolModalTab>('chart');

  const openDetail = useCallback((sym: string, tab: SymbolModalTab = 'chart') => {
    setDetailSymbol(sym);
    setDetailTab(tab);
  }, []);

  useEffect(() => {
    if (active && !fetched && !loading) loadDashboard({ watchlistOnly });
  }, [active]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (fetched) loadDashboard({ watchlistOnly });
  }, [watchlistOnly]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!watchlistOnly && (viewMode === 'cluster' || viewMode === 'charts')) setViewMode('table');
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
    if (biasFilter === 'bull') rows = rows.filter(row => row.weekly_bias === 'BULLISH');
    if (biasFilter === 'bear') rows = rows.filter(row => row.weekly_bias === 'BEARISH');
    if (biasFilter === 'neutral') rows = rows.filter(row => row.weekly_bias === 'NEUTRAL' || row.weekly_bias == null);
    if (q) rows = rows.filter(row => row.symbol.includes(q) || row.company_name?.toUpperCase().includes(q));

    return [...rows].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return sortAsc ? Number(av) - Number(bv) : Number(bv) - Number(av);
    });
  }, [scores, segment, biasFilter, query, sortKey, sortAsc]);

  const handleSort = useCallback((key: SortKey) => {
    setSortAsc(prev => sortKey === key ? !prev : key === 'rank');
    setSortKey(key);
  }, [sortKey]);

  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 44,
    overscan: 12,
  });

  const virtualItems = rowVirtualizer.getVirtualItems();
  const totalSize = rowVirtualizer.getTotalSize();

  const derivedStats = useMemo(() => {
    const withComfort = filtered.filter(r => r.comfort_score != null);
    const sweetSpot = withComfort.filter(r => r.total_score >= 70 && r.comfort_score! >= 65).length;
    const highComfort = withComfort.filter(r => r.comfort_score! >= 65).length;
    const bullish = filtered.filter(r => r.weekly_bias === 'BULLISH').length;
    const avgComfort = withComfort.length > 0
      ? (withComfort.reduce((s, r) => s + r.comfort_score!, 0) / withComfort.length).toFixed(1)
      : '-';
    return { sweetSpot, highComfort, bullish, avgComfort };
  }, [filtered]);

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

          <div className="seg-group">
            <button type="button" onClick={() => setBiasFilter('all')} className={`seg-btn ${biasFilter === 'all' ? 'active' : ''}`}>Bias</button>
            <button type="button" onClick={() => setBiasFilter('bull')} className={`seg-btn ${biasFilter === 'bull' ? 'active' : ''}`} style={biasFilter === 'bull' ? { color: 'rgb(var(--bull))' } : undefined}>Bull</button>
            <button type="button" onClick={() => setBiasFilter('bear')} className={`seg-btn ${biasFilter === 'bear' ? 'active' : ''}`} style={biasFilter === 'bear' ? { color: 'rgb(var(--bear))' } : undefined}>Bear</button>
            <button type="button" onClick={() => setBiasFilter('neutral')} className={`seg-btn ${biasFilter === 'neutral' ? 'active' : ''}`}>Neut</button>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <div className="seg-group">
              {watchlistOnly && (
                <button
                  type="button"
                  onClick={() => setViewMode('charts')}
                  title="Chart view — list + candlestick"
                  aria-label="Chart view"
                  className={`seg-btn px-2 ${viewMode === 'charts' ? 'active' : ''}`}
                >
                  <BarChart2 size={14} aria-hidden="true" />
                </button>
              )}
              {watchlistOnly && (
                <button
                  type="button"
                  onClick={() => setViewMode('cluster')}
                  title="Cluster chart"
                  aria-label="Cluster chart"
                  className={`seg-btn px-2 ${viewMode === 'cluster' ? 'active' : ''}`}
                >
                  <Crosshair size={14} aria-hidden="true" />
                </button>
              )}
              <button
                type="button"
                onClick={() => setViewMode('card')}
                title="Card view"
                aria-label="Card view"
                className={`seg-btn px-2 ${viewMode === 'card' ? 'active' : ''}`}
              >
                <LayoutGrid size={14} aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode('table')}
                title="Table view"
                aria-label="Table view"
                className={`seg-btn px-2 ${viewMode === 'table' ? 'active' : ''}`}
              >
                <List size={14} aria-hidden="true" />
              </button>
            </div>
            <button
              type="button"
              onClick={() => loadDashboard({ watchlistOnly })}
              disabled={loading}
              className="icon-btn"
              title="Refresh dashboard"
              aria-label="Refresh dashboard"
            >
              <RotateCcw size={15} aria-hidden="true" />
            </button>
          </div>
        </div>

        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          <StatCard label="Score date" value={stats.score_date || '-'} />
          <StatCard label="Sweet spot" title="Total ≥70 and Comfort ≥65" value={derivedStats.sweetSpot} tone="bull" />
          <StatCard label="High comfort" title="Comfort ≥65" value={derivedStats.highComfort} tone="accent" />
          <StatCard label="Avg comfort" title="Mean comfort score" value={derivedStats.avgComfort} />
          <StatCard label="Bullish" title="Weekly bias bullish" value={derivedStats.bullish} tone="bull" />
        </div>
      </div>

      {viewMode === 'charts' ? (
        <WatchlistSplitView scores={filtered} loading={loading} />
      ) : viewMode === 'cluster' ? (
        <ClusterChart scores={filtered} loading={loading} />
      ) : viewMode === 'card' ? (
        <div className="flex-1 overflow-y-auto p-4">
          {filtered.length === 0 && !loading && (
            <div className="flex h-48 items-center justify-center text-[13px] text-dim">
              {scores.length === 0 ? 'No scores yet. Run compute to build the dashboard.' : 'No symbols match the active filters.'}
            </div>
          )}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filtered.map(row => (
              <ScoreCard
                key={row.symbol}
                row={row}
                onOpen={openDetail}
              />
            ))}
          </div>
        </div>
      ) : (
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
                    <span className="inline-flex items-center gap-0.5">
                      {header.label}
                      {header.sortable && (
                        <span className="inline-flex opacity-60">
                          {sortKey === header.key
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
              {virtualItems.length > 0 && (
                <tr><td colSpan={HEADERS.length} style={{ height: virtualItems[0].start, padding: 0, border: 'none' }} /></tr>
              )}
              {virtualItems.map(item => {
                const row = filtered[item.index];
                return (
                  <ScoreRow
                    key={row.symbol}
                    row={row}
                    onOpen={openDetail}
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
      )}

      <div className="flex shrink-0 items-center justify-between border-t border-border bg-panel/80 px-4 py-2 text-[11px] text-ghost">
        <span className="num">{filtered.length}/{scores.length} symbols</span>
        <span className="flex gap-3">
          <span style={{ color: 'rgb(var(--violet))' }}>F&O {scores.filter(row => row.is_fno === true).length}</span>
          <span style={{ color: 'rgb(var(--bull))' }}>Equity {scores.filter(row => row.is_fno !== true).length}</span>
        </span>
      </div>

      {detailSymbol && (
        <SymbolModal
          symbol={detailSymbol}
          initialTab={detailTab}
          onClose={() => setDetailSymbol(null)}
        />
      )}
    </div>
  );
}

function StatCard({ label, value, tone, title }: { label: string; value: string | number; tone?: 'bull' | 'accent'; title?: string }) {
  const color = tone === 'bull' ? 'rgb(var(--bull))' : tone === 'accent' ? 'rgb(var(--accent))' : 'rgb(var(--fg))';
  return (
    <div className="metric-card" title={title}>
      <div className="text-[10px] font-black uppercase text-ghost">{label}</div>
      <div className="num mt-1 truncate text-[19px] font-black" style={{ color }}>{value}</div>
    </div>
  );
}

function ScoreCard({
  row,
  onOpen,
}: {
  row: ScoredSymbol;
  onOpen: (sym: string, tab?: 'chart' | 'oc') => void;
}) {
  return (
    <div
      className="rounded-lg border border-border bg-panel p-3 cursor-pointer transition-colors hover:border-accent/40 hover:bg-lift/60"
      onClick={() => onOpen(row.symbol, 'chart')}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1">
            <span className="text-ticker text-fg">{row.symbol}</span>
            {row.is_fno && <span className="chip h-4 min-h-0 px-1" style={{ color: 'rgb(var(--violet))' }}>F&O</span>}
            {row.is_watchlist && <span className="chip h-4 min-h-0 px-1" style={{ color: 'rgb(var(--amber))' }}>WL</span>}
            {row.is_new_watchlist && <span className="chip h-4 min-h-0 px-1" title="New to watchlist in the last 7 days" style={{ color: 'rgb(var(--accent))' }}>NEW</span>}
            {row.bb_squeeze && <span className="chip h-4 min-h-0 px-1" style={{ color: 'rgb(var(--violet))' }}>SQ{row.squeeze_days}</span>}
            {row.nr7 && <span className="chip h-4 min-h-0 px-1" style={{ color: 'rgb(var(--sky))' }}>NR7</span>}
          </div>
          {row.company_name && <div className="mt-0.5 max-w-full truncate text-[10px] text-ghost">{row.company_name}</div>}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="num text-[10px] text-ghost">#{row.rank}</span>
          <button
            type="button"
            onClick={event => { event.stopPropagation(); onOpen(row.symbol, 'oc'); }}
            className="text-[10px] font-black text-accent opacity-60 hover:opacity-100"
            title="View option chain"
          >
            OC
          </button>
        </div>
      </div>

      <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1">
        <ScoreBar value={row.total_score} color="rgb(var(--accent))" label="Total" />
        <ScoreBar value={row.momentum_score} color="rgb(var(--amber))" label="Mom" />
        <ScoreBar value={row.trend_score} color="rgb(var(--bull))" label="Trend" />
        <ScoreBar value={row.volatility_score} color="rgb(var(--violet))" label="Vol" />
      </div>

      <div className="mt-2 flex items-center justify-between text-[11px]">
        <span className="num text-ghost">ADX <span className="text-fg">{row.adx_14 != null ? row.adx_14.toFixed(0) : '-'}</span></span>
        <span className="num text-ghost">RSI <span style={{ color: rsiColor(row.rsi_14) }}>{row.rsi_14 != null ? row.rsi_14.toFixed(0) : '-'}</span></span>
        <span className="num text-ghost">ADV <span className="text-fg">{fmtAdv(row.adv_20_cr)}</span></span>
        {row.comfort_score != null && (
          <span className="num text-ghost" title={row.comfort_interpretation ?? undefined}>
            C <span style={{ color: comfortColor(row.comfort_score) }}>{row.comfort_score.toFixed(0)}</span>
          </span>
        )}
        <span
          className="num font-black"
          style={{ color: row.weekly_bias === 'BULLISH' ? 'rgb(var(--bull))' : row.weekly_bias === 'BEARISH' ? 'rgb(var(--bear))' : 'rgb(var(--ghost))' }}
        >
          {row.weekly_bias === 'BULLISH' ? 'UP' : row.weekly_bias === 'BEARISH' ? 'DN' : '-'}
        </span>
      </div>

    </div>
  );
}

function ScoreRow({
  row,
  onOpen,
}: {
  row: ScoredSymbol;
  onOpen: (sym: string, tab?: 'chart' | 'oc') => void;
}) {
  return (
    <>
      <tr className="group cursor-pointer" onClick={() => onOpen(row.symbol, 'chart')}>
        <td className="text-center num text-dim">{row.rank}</td>
        <td className="whitespace-nowrap">
          <div className="flex items-center gap-2">
            <span className="text-ticker text-fg">{row.symbol}</span>
            {row.is_fno && <span className="chip h-5 min-h-0 px-1.5" style={{ color: 'rgb(var(--violet))' }}>F&O</span>}
            {row.is_watchlist && <span className="chip h-5 min-h-0 px-1.5" style={{ color: 'rgb(var(--amber))' }}>WL</span>}
            {row.is_new_watchlist && <span className="chip h-5 min-h-0 px-1.5" title="New to watchlist in the last 7 days" style={{ color: 'rgb(var(--accent))' }}>NEW</span>}
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
        <td className="text-right num" title={row.comfort_interpretation ?? undefined} style={{ color: comfortColor(row.comfort_score) }}>
          {row.comfort_score != null ? row.comfort_score.toFixed(0) : '-'}
        </td>
        <td className="text-center">
          <button
            type="button"
            onClick={event => {
              event.stopPropagation();
              onOpen(row.symbol, 'oc');
            }}
            className="text-[10px] font-black text-accent opacity-0 transition-opacity group-hover:opacity-100"
            title="View option chain"
          >
            OC
          </button>
        </td>
      </tr>
    </>
  );
}

function ScoreBar({ value, color, label }: { value: number; color: string; label?: string }) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div className="flex items-center gap-2">
      {label && <span className="w-8 shrink-0 text-[9px] font-black uppercase text-ghost">{label}</span>}
      <div className="flex flex-1 items-center justify-end gap-2">
        <span className="num text-[11px] font-black" style={{ color }}>{value.toFixed(0)}</span>
        <div className="h-1.5 w-[54px] overflow-hidden rounded-full bg-border">
          <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
        </div>
      </div>
    </div>
  );
}

function comfortColor(v: number | null | undefined): string {
  if (v == null) return 'rgb(var(--ghost))';
  if (v >= 80) return 'rgb(var(--bull))';
  if (v >= 65) return 'rgb(var(--accent))';
  if (v >= 50) return 'rgb(var(--amber))';
  if (v >= 35) return 'rgb(var(--bear))';
  return 'rgb(var(--bear))';
}

function rsiColor(v: number | null | undefined): string {
  if (v == null) return 'rgb(var(--ghost))';
  if (v >= 70) return 'rgb(var(--bear))';
  if (v <= 30) return 'rgb(var(--bull))';
  return 'rgb(var(--amber))';
}
