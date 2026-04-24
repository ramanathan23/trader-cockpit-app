'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ScoredSymbol } from '@/domain/dashboard';
import type { SortKey, Segment, StageFilter } from './dashboardTypes';
import type { SymbolModalTab } from './SymbolModal';

interface UseDashboardStateProps {
  scores: ScoredSymbol[];
  fetched: boolean;
  loading: boolean;
  loadDashboard: (opts: { watchlistOnly: boolean }) => void;
}

/** Manages all filter, sort, and detail-modal state for the Dashboard panel. */
export function useDashboardState({ scores, fetched, loading, loadDashboard }: UseDashboardStateProps) {
  const [watchlistOnly, setWatchlistOnly] = useState(false);
  const [newOnly,       setNewOnly]       = useState(false);
  const [viewMode,      setViewMode]      = useState<'card' | 'table' | 'cluster' | 'charts'>('table');
  const [segment,       setSegment]       = useState<Segment>('all');
  const [stageFilter,   setStageFilter]   = useState<StageFilter>('all');
  const [query,         setQuery]         = useState('');
  const [sortKey,       setSortKey]       = useState<SortKey>('total_score');
  const [sortAsc,       setSortAsc]       = useState(false);
  const [detailSymbol,  setDetailSymbol]  = useState<string | null>(null);
  const [detailTab,     setDetailTab]     = useState<SymbolModalTab>('chart');

  const openDetail = useCallback((sym: string, tab: SymbolModalTab = 'chart') => {
    setDetailSymbol(sym); setDetailTab(tab);
  }, []);

  useEffect(() => { if (fetched) loadDashboard({ watchlistOnly }); }, [watchlistOnly]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!watchlistOnly && (viewMode === 'cluster' || viewMode === 'charts')) setViewMode('table'); }, [watchlistOnly]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (segment === 'all') { setSortKey('total_score'); setSortAsc(false); }
    else                   { setSortKey('rank');        setSortAsc(true);  }
  }, [segment]);

  const filtered = useMemo(() => {
    const q = query.trim().toUpperCase();
    let rows = scores;
    if (segment === 'fno')    rows = rows.filter(r => r.is_fno === true);
    if (segment === 'equity') rows = rows.filter(r => r.is_fno !== true);
    if (stageFilter === 'stage2') rows = rows.filter(r => r.stage === 'STAGE_2');
    if (stageFilter === 'stage4') rows = rows.filter(r => r.stage === 'STAGE_4');
    if (newOnly) rows = rows.filter(r => r.is_new_watchlist);
    if (q) rows = rows.filter(r => r.symbol.includes(q) || r.company_name?.toUpperCase().includes(q));
    return [...rows].sort((a, b) => {
      const av = a[sortKey]; const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return sortAsc ? Number(av) - Number(bv) : Number(bv) - Number(av);
    });
  }, [scores, segment, stageFilter, newOnly, query, sortKey, sortAsc]);

  const handleSort = useCallback((key: SortKey) => {
    setSortAsc(prev => sortKey === key ? !prev : key === 'rank');
    setSortKey(key);
  }, [sortKey]);

  return {
    watchlistOnly, setWatchlistOnly,
    newOnly, setNewOnly,
    viewMode, setViewMode,
    segment, setSegment,
    stageFilter, setStageFilter,
    query, setQuery,
    sortKey, sortAsc, handleSort,
    detailSymbol, setDetailSymbol,
    detailTab, openDetail,
    filtered,
  };
}
