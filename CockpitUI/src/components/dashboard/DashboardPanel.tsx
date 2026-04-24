'use client';

import { useEffect, useMemo } from 'react';
import { useDashboard } from '@/hooks/useDashboard';
import { useLivePrices } from '@/hooks/useLivePrices';
import { comfortColor } from '@/lib/scoreColors';
import type { DashboardResponse } from '@/domain/dashboard';
import { ClusterChart } from './ClusterChart';
import { WatchlistSplitView } from './WatchlistSplitView';
import { SymbolModal } from './SymbolModal';
import { DashboardFilters } from './DashboardFilters';
import { DashboardTable } from './DashboardTable';
import { StatCard } from './StatCard';
import { ScoreCard } from './ScoreCard';
import { useDashboardState } from './useDashboardState';

interface DashboardPanelProps {
  active: boolean;
  initialData?: DashboardResponse | null;
  marketOpen: boolean;
}

/** Root dashboard panel — orchestrates filters, views, and derived stats. */
export function DashboardPanel({ active, initialData, marketOpen }: DashboardPanelProps) {
  const { stats, scores, loading, fetched, loadDashboard } = useDashboard(initialData);
  const state = useDashboardState({ scores, fetched, loading, loadDashboard });
  const { watchlistOnly, setWatchlistOnly, viewMode, setViewMode, segment, setSegment,
          stageFilter, setStageFilter, query, setQuery, sortKey, sortAsc, handleSort,
          detailSymbol, setDetailSymbol, detailTab, openDetail, filtered } = state;

  useEffect(() => {
    if (active && !fetched && !loading) loadDashboard({ watchlistOnly });
  }, [active]); // eslint-disable-line react-hooks/exhaustive-deps

  const filteredSymbols = useMemo(() => filtered.slice(0, 200).map(r => r.symbol), [filtered]);
  const livePrices = useLivePrices(filteredSymbols, marketOpen);

  const derivedStats = useMemo(() => {
    const withComfort = filtered.filter(r => r.comfort_score != null);
    return {
      sweetSpot:   withComfort.filter(r => r.total_score >= 70 && r.comfort_score! >= 65).length,
      highComfort: withComfort.filter(r => r.comfort_score! >= 65).length,
      stage2:      filtered.filter(r => r.stage === 'STAGE_2').length,
      avgComfort:  withComfort.length > 0
        ? (withComfort.reduce((s, r) => s + r.comfort_score!, 0) / withComfort.length).toFixed(1)
        : '-',
    };
  }, [filtered]);

  const emptyMsg = scores.length === 0
    ? 'No scores yet. Run compute to build the dashboard.'
    : 'No symbols match the active filters.';

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="border-b border-border bg-panel/72 px-4 py-3">
        <DashboardFilters
          query={query} onQuery={setQuery}
          watchlistOnly={watchlistOnly} onWatchlistOnly={setWatchlistOnly}
          segment={segment} onSegment={setSegment}
          stageFilter={stageFilter} onStageFilter={setStageFilter}
          viewMode={viewMode} onViewMode={setViewMode}
          loading={loading} onRefresh={() => loadDashboard({ watchlistOnly })}
        />
        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          <StatCard label="Score date"   value={stats.score_date || '-'} />
          <StatCard label="Sweet spot"   title="Total ≥70 and Comfort ≥65" value={derivedStats.sweetSpot}   tone="bull"   />
          <StatCard label="High comfort" title="Comfort ≥65"               value={derivedStats.highComfort} tone="accent" />
          <StatCard label="Avg comfort"  title="Mean comfort score"         value={derivedStats.avgComfort} />
          <StatCard label="Stage 2"      title="Uptrend stocks"             value={derivedStats.stage2}      tone="bull"   />
        </div>
      </div>

      {viewMode === 'charts' ? (
        <WatchlistSplitView scores={filtered} loading={loading} marketOpen={marketOpen} livePrices={livePrices} />
      ) : viewMode === 'cluster' ? (
        <ClusterChart scores={filtered} loading={loading} />
      ) : viewMode === 'card' ? (
        <div className="flex-1 overflow-y-auto p-4">
          {filtered.length === 0 && !loading && <div className="flex h-48 items-center justify-center text-[13px] text-dim">{emptyMsg}</div>}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filtered.map(row => <ScoreCard key={row.symbol} row={row} livePrice={livePrices[row.symbol]} marketOpen={marketOpen} onOpen={openDetail} />)}
          </div>
        </div>
      ) : (
        <DashboardTable rows={filtered} livePrices={livePrices} marketOpen={marketOpen}
          sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} onOpen={openDetail} emptyMsg={emptyMsg} />
      )}

      <div className="flex shrink-0 items-center justify-between border-t border-border bg-panel/80 px-4 py-2 text-[11px] text-ghost">
        <span className="num">{filtered.length}/{scores.length} symbols</span>
        <span className="flex gap-3">
          <span className="text-violet">F&O {scores.filter(r => r.is_fno === true).length}</span>
          <span className="text-bull">Equity {scores.filter(r => r.is_fno !== true).length}</span>
        </span>
      </div>

      {detailSymbol && <SymbolModal symbol={detailSymbol} initialTab={detailTab} onClose={() => setDetailSymbol(null)} />}
    </div>
  );
}
