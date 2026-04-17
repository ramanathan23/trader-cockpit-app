'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useDashboard } from '@/hooks/useDashboard';
import { DailyChart } from './DailyChart';
import { OptionChainPanel } from './OptionChainPanel';
import { fmt2, fmtAdv } from '@/lib/fmt';
import type { ScoredSymbol } from '@/domain/dashboard';

type SortKey = 'rank' | 'total_score' | 'momentum_score' | 'trend_score' | 'volatility_score' | 'structure_score' | 'adx_14' | 'rsi_14';
type Segment = 'all' | 'fno' | 'equity';

interface DashboardPanelProps {
  active: boolean;
}

export function DashboardPanel({ active }: DashboardPanelProps) {
  const { stats, scores, loading, computing, hasMore, fetched, loadDashboard, loadMore, triggerCompute } = useDashboard();
  const [watchlistOnly, setWatchlistOnly] = useState(false);
  const [segment, setSegment] = useState<Segment>('all');
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('rank');
  const [sortAsc, setSortAsc] = useState(true);
  const [ocSymbol, setOcSymbol] = useState<string | null>(null);
  const [chartSymbol, setChartSymbol] = useState<string | null>(null);

  useEffect(() => {
    if (active && !fetched && !loading) loadDashboard({ watchlistOnly });
  }, [active]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (fetched) loadDashboard({ watchlistOnly });
  }, [watchlistOnly]); // eslint-disable-line react-hooks/exhaustive-deps

  // Reset sort to the natural order for the active segment view
  useEffect(() => {
    if (segment === 'all') {
      setSortKey('total_score');
      setSortAsc(false);
    } else {
      setSortKey('rank');
      setSortAsc(true);
    }
  }, [segment]);

  const handleSort = useCallback((key: SortKey) => {
    setSortAsc(prev => sortKey === key ? !prev : key === 'rank');
    setSortKey(key);
  }, [sortKey]);

  const filtered = useMemo(() => {
    let rows = scores;
    if (segment === 'fno')    rows = rows.filter(r => r.is_fno === true);
    if (segment === 'equity') rows = rows.filter(r => r.is_fno !== true);
    if (query) {
      const q = query.toUpperCase();
      rows = rows.filter(r => r.symbol.includes(q) || r.company_name?.toUpperCase().includes(q));
    }
    const sorted = [...rows].sort((a, b) => {
      const av = a[sortKey] ?? 0;
      const bv = b[sortKey] ?? 0;
      return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
    return sorted;
  }, [scores, segment, query, sortKey, sortAsc]);

  const toggleExpand = useCallback((sym: string) => {
    setChartSymbol(sym);
  }, []);

  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 40,
    overscan: 10,
  });
  const virtualItems = rowVirtualizer.getVirtualItems();
  const totalSize   = rowVirtualizer.getTotalSize();

  // Infinite scroll: load more when near bottom
  const handleScroll = useCallback(() => {
    const el = parentRef.current;
    if (!el || loading || !hasMore) return;
    const threshold = 200;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < threshold) {
      loadMore({ watchlistOnly, segment: segment !== 'all' ? segment : undefined });
    }
  }, [loading, hasMore, loadMore, watchlistOnly, segment]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="shrink-0 flex items-center flex-wrap gap-2.5 px-3 py-2 bg-panel border-b border-border">
        {/* Search */}
        <input
          type="text" value={query} onChange={e => setQuery(e.target.value)}
          placeholder="Search symbol…"
          className="bg-card border border-border text-fg text-[11px] rounded-[4px] px-2.5 py-1 w-40 focus:outline-none focus:border-accent"
          style={{ colorScheme: 'inherit' }}
        />

        {/* Watchlist filter */}
        <div className="seg-group">
          <button onClick={() => setWatchlistOnly(false)}
            className={`seg-btn ${!watchlistOnly ? 'active' : ''}`}
            style={!watchlistOnly ? { color: '#2d7ee8' } : undefined}>ALL</button>
          <button onClick={() => setWatchlistOnly(true)}
            className={`seg-btn ${watchlistOnly ? 'active' : ''}`}
            style={watchlistOnly ? { color: '#e8933a' } : undefined}>WATCHLIST</button>
        </div>

        {/* Segment filter */}
        <div className="seg-group">
          <button onClick={() => setSegment('all')}
            className={`seg-btn ${segment === 'all' ? 'active' : ''}`}
            style={segment === 'all' ? { color: '#5a7796' } : undefined}>ALL</button>
          <button onClick={() => setSegment('fno')}
            className={`seg-btn ${segment === 'fno' ? 'active' : ''}`}
            style={segment === 'fno' ? { color: '#9b72f7' } : undefined}>F&amp;O</button>
          <button onClick={() => setSegment('equity')}
            className={`seg-btn ${segment === 'equity' ? 'active' : ''}`}
            style={segment === 'equity' ? { color: '#0dbd7d' } : undefined}>EQ</button>
        </div>

        {/* Stats pills */}
        {stats.score_date && (
          <div className="flex items-center gap-3 text-[10px]">
            <span className="text-ghost">Date: <b className="text-fg">{stats.score_date}</b></span>
            <span className="text-ghost">Scored: <b className="text-fg">{stats.total_scored}</b></span>
            <span className="text-ghost">Avg: <b className="num text-fg">{stats.avg_score}</b></span>
            <span className="text-ghost">High: <b className="num" style={{ color: '#0dbd7d' }}>{stats.high_conviction}</b></span>
          </div>
        )}

        <div className="ml-auto flex items-center gap-2">
          <button onClick={triggerCompute} disabled={computing}
            className="text-[10px] font-bold px-3 py-1 rounded-[4px] border border-accent/40 text-accent hover:bg-accent/10 disabled:opacity-50 transition-all">
            {computing ? '⏳ COMPUTING…' : '↻ COMPUTE'}
          </button>
          <button onClick={() => loadDashboard({ watchlistOnly })} disabled={loading}
            className="text-[10px] font-semibold text-ghost hover:text-fg transition-colors px-1">
            {loading ? '…' : '↻'}
          </button>
        </div>
      </div>

      {/* Table */}
      <div ref={parentRef} className="flex-1 overflow-auto" onScroll={handleScroll}>
        <table className="w-full text-[11px] border-collapse">
          <thead className="sticky top-0 bg-panel z-10">
            <tr className="border-b border-border">
              {HEADERS.map(h => (
                <th key={h.key} title={h.title}
                    onClick={() => h.sortable && handleSort(h.key as SortKey)}
                    className={`px-2.5 py-2 text-left font-bold text-[9px] tracking-[0.12em] whitespace-nowrap select-none uppercase ${h.sortable ? 'cursor-pointer hover:text-fg' : ''}`}
                    style={{ color: sortKey === h.key ? '#2d7ee8' : undefined, textAlign: h.align as 'left' | 'right' | 'center' }}>
                  {h.label}{sortKey === h.key ? (sortAsc ? ' ↑' : ' ↓') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {virtualItems.length > 0 && (
              <tr><td colSpan={13} style={{ height: virtualItems[0].start, padding: 0, border: 'none' }} /></tr>
            )}
            {virtualItems.map(vi => (
              <ScoreRow key={filtered[vi.index].symbol} row={filtered[vi.index]}
                onToggle={toggleExpand}
                onOptionChain={setOcSymbol} />
            ))}
            {virtualItems.length > 0 && (
              <tr><td colSpan={13} style={{ height: totalSize - virtualItems[virtualItems.length - 1].end, padding: 0, border: 'none' }} /></tr>
            )}
          </tbody>
        </table>

        {filtered.length === 0 && !loading && (
          <div className="flex items-center justify-center py-16 text-ghost text-xs">
            {scores.length === 0 ? 'No scores computed yet — click COMPUTE to run' : 'No matches'}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="shrink-0 flex items-center justify-between px-4 py-1 bg-panel border-t border-border text-[10px] text-ghost">
        <span className="num tabular-nums">{filtered.length}/{scores.length} symbols</span>
        <span className="flex gap-3">
          <span style={{ color: '#9b72f7' }}>F&amp;O: {scores.filter(s => s.is_fno === true).length}</span>
          <span style={{ color: '#0dbd7d' }}>EQ: {scores.filter(s => s.is_fno !== true).length}</span>
        </span>
      </div>

      {/* Chart modal */}
      {chartSymbol && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
             onClick={() => setChartSymbol(null)}>
          <div className="bg-panel border border-border rounded-lg shadow-2xl overflow-hidden"
               style={{ width: 900, maxWidth: '95vw' }}
               onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="font-bold text-fg">{chartSymbol}</span>
                {scores.find(s => s.symbol === chartSymbol)?.is_fno && (
                  <span className="text-[7px] font-black px-1 py-0.5 rounded-sm"
                        style={{ background: '#9b72f718', color: '#9b72f7' }}>F&amp;O</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {scores.find(s => s.symbol === chartSymbol)?.is_fno && (
                  <button onClick={() => { setChartSymbol(null); setOcSymbol(chartSymbol); }}
                    className="text-[10px] font-bold text-accent hover:text-fg transition-colors px-2 py-1 border border-accent/40 rounded-sm">OC</button>
                )}
                <button onClick={() => setChartSymbol(null)}
                  className="text-ghost hover:text-fg transition-colors text-base leading-none px-1">✕</button>
              </div>
            </div>
            <DailyChart symbol={chartSymbol} height={380} />
          </div>
        </div>
      )}

      {/* Option chain modal */}
      {ocSymbol && <OptionChainPanel symbol={ocSymbol} onClose={() => setOcSymbol(null)} scoreData={scores.find(s => s.symbol === ocSymbol)} />}
    </div>
  );
}

// ── Score row with expandable chart ──────────────────────────────────────────

function ScoreRow({ row, onToggle, onOptionChain }: {
  row: ScoredSymbol;
  onToggle: (sym: string) => void; onOptionChain: (sym: string) => void;
}) {
  return (
    <>
      <tr className="border-b border-border transition-colors cursor-pointer group hover:bg-lift"
          onClick={() => onToggle(row.symbol)}>
        <td className="px-2.5 py-2 text-center num tabular-nums text-dim">{row.rank}</td>
        <td className="px-2.5 py-2 whitespace-nowrap">
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-[12px] text-fg">{row.symbol}</span>
            {row.is_fno && (
              <span className="text-[7px] font-black px-1 py-0.5 rounded-sm" style={{ background: '#9b72f718', color: '#9b72f7' }}>F&O</span>
            )}
            {row.is_watchlist && (
              <span className="text-[7px] font-black px-1 py-0.5 rounded-sm" style={{ background: '#e8933a18', color: '#e8933a' }}>WL</span>
            )}
            {row.bb_squeeze && (
              <span className="text-[7px] font-black px-1 py-0.5 rounded-sm" style={{ background: '#9b72f718', color: '#9b72f7' }}
                    title={`BB Squeeze ${row.squeeze_days}d`}>SQ{row.squeeze_days}</span>
            )}
            {row.nr7 && (
              <span className="text-[7px] font-black px-1 py-0.5 rounded-sm" style={{ background: '#38b6ff18', color: '#38b6ff' }}>NR7</span>
            )}
          </div>
          {row.company_name && <div className="text-[9px] text-ghost truncate max-w-[160px]">{row.company_name}</div>}
        </td>
        <td className="px-2.5 py-2 text-right">
          <ScoreBar value={row.total_score} color="#2d7ee8" />
        </td>
        <td className="px-2.5 py-2 text-right">
          <ScoreBar value={row.momentum_score} color="#e8933a" />
        </td>
        <td className="px-2.5 py-2 text-right">
          <ScoreBar value={row.trend_score} color="#0dbd7d" />
        </td>
        <td className="px-2.5 py-2 text-right">
          <ScoreBar value={row.volatility_score} color="#9b72f7" />
        </td>
        <td className="px-2.5 py-2 text-right">
          <ScoreBar value={row.structure_score} color="#38b6ff" />
        </td>
        <td className="px-2.5 py-2 text-right num tabular-nums text-dim">{row.adx_14 != null ? row.adx_14.toFixed(0) : '—'}</td>
        <td className="px-2.5 py-2 text-right num tabular-nums" style={{ color: rsiColor(row.rsi_14) }}>
          {row.rsi_14 != null ? row.rsi_14.toFixed(0) : '—'}
        </td>
        <td className="px-2.5 py-2 text-right num tabular-nums text-dim">
          {row.adv_20_cr != null ? fmtAdv(row.adv_20_cr) : '—'}
        </td>
        <td className="px-2.5 py-2 text-center text-[9px] font-bold"
            style={{ color: row.weekly_bias === 'BULLISH' ? '#0dbd7d' : row.weekly_bias === 'BEARISH' ? '#f23d55' : '#5a7796' }}>
          {row.weekly_bias === 'BULLISH' ? '↑' : row.weekly_bias === 'BEARISH' ? '↓' : '·'}
        </td>
        <td className="px-2.5 py-2 text-right num tabular-nums text-dim">{fmt2(row.prev_day_close)}</td>
        <td className="px-2.5 py-2">
          <button onClick={e => { e.stopPropagation(); onOptionChain(row.symbol); }}
            className="text-[9px] font-bold text-accent hover:text-fg transition-colors opacity-0 group-hover:opacity-100"
            title="View option chain">
            OC
          </button>
        </td>
      </tr>
    </>
  );
}

// ── ScoreBar ─────────────────────────────────────────────────────────────────

function ScoreBar({ value, color }: { value: number; color: string }) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div className="flex items-center gap-1.5 justify-end">
      <span className="num tabular-nums text-[10px] font-bold" style={{ color }}>{value.toFixed(0)}</span>
      <div className="w-[40px] h-[4px] rounded-full bg-border overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function rsiColor(v: number | null | undefined): string {
  if (v == null) return '#5a7796';
  if (v >= 70) return '#f23d55';
  if (v <= 30) return '#0dbd7d';
  return '#e8933a';
}

// ── Headers ──────────────────────────────────────────────────────────────────

const HEADERS: { key: string; label: string; title: string; align: string; sortable: boolean }[] = [
  { key: 'rank',             label: '#',     title: 'Rank',                      align: 'center', sortable: true },
  { key: 'symbol',           label: 'SYMBOL',title: 'Symbol + tags',             align: 'left',   sortable: false },
  { key: 'total_score',      label: 'TOTAL', title: 'Total unified score (0-100)',align: 'right',  sortable: true },
  { key: 'momentum_score',   label: 'MOM',   title: 'Momentum (RSI + MACD + ROC + Vol)', align: 'right', sortable: true },
  { key: 'trend_score',      label: 'TREND', title: 'Trend (ADX + DI + EMA stack + Weekly)', align: 'right', sortable: true },
  { key: 'volatility_score', label: 'VOL',   title: 'Volatility (BB Squeeze + ATR contraction + NR7)', align: 'right', sortable: true },
  { key: 'structure_score',  label: 'STRUCT',title: 'Structure (52W proximity + RS + Vol trend)', align: 'right', sortable: true },
  { key: 'adx_14',           label: 'ADX',   title: 'ADX(14) — trend strength',  align: 'right',  sortable: true },
  { key: 'rsi_14',           label: 'RSI',   title: 'RSI(14)',                    align: 'right',  sortable: true },
  { key: 'adv',              label: 'ADV',   title: 'Avg Daily Value (₹Cr)',      align: 'right',  sortable: false },
  { key: 'weekly',           label: 'W',     title: 'Weekly bias',                align: 'center', sortable: false },
  { key: 'close',            label: 'CLOSE', title: 'Previous day close',         align: 'right',  sortable: false },
  { key: 'oc',               label: 'OC',    title: 'Option chain',               align: 'center', sortable: false },
];
