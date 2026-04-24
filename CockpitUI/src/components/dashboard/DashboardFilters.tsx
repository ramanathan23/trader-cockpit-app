'use client';

import { BarChart2, Crosshair, LayoutGrid, List, RotateCcw } from 'lucide-react';
import { cn } from '@/lib/cn';
import type { Segment, StageFilter } from './dashboardTypes';

const STAGE_COLOR: Record<string, string> = { stage1: 'text-amber', stage2: 'text-bull', stage3: 'text-violet', stage4: 'text-bear' };

interface DashboardFiltersProps {
  query: string;
  onQuery: (q: string) => void;
  watchlistOnly: boolean;
  onWatchlistOnly: (v: boolean) => void;
  segment: Segment;
  onSegment: (s: Segment) => void;
  stageFilter: StageFilter;
  onStageFilter: (s: StageFilter) => void;
  viewMode: 'card' | 'table' | 'cluster' | 'charts';
  onViewMode: (v: 'card' | 'table' | 'cluster' | 'charts') => void;
  loading: boolean;
  onRefresh: () => void;
}

/** Filter toolbar for the Dashboard panel — search, watchlist, segment, stage, view mode. */
export function DashboardFilters({
  query, onQuery, watchlistOnly, onWatchlistOnly,
  segment, onSegment, stageFilter, onStageFilter,
  viewMode, onViewMode, loading, onRefresh,
}: DashboardFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <input type="text" value={query} onChange={e => onQuery(e.target.value)}
        placeholder="Search symbol" className="field w-44 text-[12px]" style={{ colorScheme: 'inherit' }} />

      <div className="seg-group">
        <button type="button" onClick={() => onWatchlistOnly(false)} className={`seg-btn ${!watchlistOnly ? 'active' : ''}`}>All</button>
        <button type="button" onClick={() => onWatchlistOnly(true)}
          className={cn('seg-btn', watchlistOnly && 'active text-amber')}>Watchlist</button>
      </div>

      <div className="seg-group">
        {(['all', 'fno', 'equity'] as Segment[]).map(s => (
          <button key={s} type="button" onClick={() => onSegment(s)}
            className={cn('seg-btn', segment === s && 'active', segment === s && s === 'fno' && 'text-violet', segment === s && s === 'equity' && 'text-bull')}>
            {s === 'fno' ? 'F&O' : s === 'equity' ? 'Equity' : 'All'}
          </button>
        ))}
      </div>

      <div className="seg-group">
        {(['all','stage1','stage2','stage3','stage4'] as StageFilter[]).map((sf, i) => (
          <button key={sf} type="button" onClick={() => onStageFilter(sf)}
            className={cn('seg-btn', stageFilter === sf && 'active', stageFilter === sf && STAGE_COLOR[sf])}>
            {sf === 'all' ? 'Stage' : `S${i}`}
          </button>
        ))}
      </div>

      <div className="ml-auto flex items-center gap-2">
        <div className="seg-group">
          {watchlistOnly && (
            <button type="button" onClick={() => onViewMode('charts')} title="Chart view" className={`seg-btn px-2 ${viewMode === 'charts' ? 'active' : ''}`}><BarChart2 size={14} /></button>
          )}
          {watchlistOnly && (
            <button type="button" onClick={() => onViewMode('cluster')} title="Cluster chart" className={`seg-btn px-2 ${viewMode === 'cluster' ? 'active' : ''}`}><Crosshair size={14} /></button>
          )}
          <button type="button" onClick={() => onViewMode('card')}  title="Card view"  className={`seg-btn px-2 ${viewMode === 'card'  ? 'active' : ''}`}><LayoutGrid size={14} /></button>
          <button type="button" onClick={() => onViewMode('table')} title="Table view" className={`seg-btn px-2 ${viewMode === 'table' ? 'active' : ''}`}><List size={14} /></button>
        </div>
        <button type="button" onClick={onRefresh} disabled={loading} className="icon-btn" title="Refresh dashboard">
          <RotateCcw size={15} />
        </button>
      </div>
    </div>
  );
}
