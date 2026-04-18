'use client';

import { useEffect, useMemo, useState } from 'react';
import { useScreener } from '@/hooks/useScreener';
import { computeBreadthStats } from '@/domain/screener';
import { ScreenerFilters } from './ScreenerFilters';
import { ScreenerTable } from './ScreenerTable';
import { ScreenerCards } from './ScreenerCards';
import { ScreenerStatsBar } from './ScreenerStatsBar';

interface ScreenerPanelProps {
  active: boolean;
}

export function ScreenerPanel({ active }: ScreenerPanelProps) {
  const [viewMode, setViewMode] = useState<'card' | 'table'>('table');

  const {
    filteredRows, loading, hasMore,
    query, setQuery,
    range, setRange,
    presets, togglePreset,
    fnoOnly, setFnoOnly,
    sortCol, sortAsc, sortBy,
    loadScreener, loadMore, resetFilters,
    totalCount,
  } = useScreener();

  const breadth = useMemo(() => computeBreadthStats(filteredRows), [filteredRows]);

  // Auto-load on first activation
  useEffect(() => {
    if (active && totalCount === 0 && !loading) {
      loadScreener();
    }
  }, [active]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <ScreenerFilters
        query={query}            onQuery={setQuery}
        range={range}            onRange={setRange}
        presets={presets}        onPreset={togglePreset}
        fnoOnly={fnoOnly}        onFnoOnly={setFnoOnly}
        onReset={resetFilters}
        totalCount={totalCount}  filteredCount={filteredRows.length}
        loading={loading}        onRefresh={loadScreener}
        viewMode={viewMode}      onViewMode={setViewMode}
      />

      <ScreenerStatsBar stats={breadth} total={filteredRows.length} />

      {viewMode === 'table'
        ? <ScreenerTable rows={filteredRows} sortCol={sortCol} sortAsc={sortAsc} onSort={sortBy} loading={loading} hasMore={hasMore} onLoadMore={loadMore} />
        : <ScreenerCards rows={filteredRows} loading={loading} hasMore={hasMore} onLoadMore={loadMore} />
      }
    </div>
  );
}
