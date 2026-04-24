'use client';

import { useEffect, useMemo, useState } from 'react';
import { useScreener } from '@/hooks/useScreener';
import { computeBreadthStats } from '@/domain/screener';
import { ScreenerFilters } from './ScreenerFilters';
import { ScreenerTable } from './ScreenerTable';
import { ScreenerCards } from './ScreenerCards';
import { ScreenerStatsBar } from './ScreenerStatsBar';
import { SymbolModal } from '@/components/dashboard/SymbolModal';

interface ScreenerPanelProps {
  active: boolean;
  viewMode: 'card' | 'table';
  onViewMode: (v: 'card' | 'table') => void;
  marketOpen: boolean;
}

export function ScreenerPanel({ active, viewMode, onViewMode, marketOpen }: ScreenerPanelProps) {
  const effectiveMode: 'card' | 'table' = viewMode === 'table' ? 'table' : 'card';

  const {
    rows, filteredRows, loading, hasMore,
    query, setQuery,
    range, setRange,
    presets, togglePreset,
    fnoOnly, setFnoOnly,
    sortCol, sortAsc, sortBy,
    loadScreener, loadMore, resetFilters,
    totalCount,
  } = useScreener();

  const [detailSymbol, setDetailSymbol] = useState<string | null>(null);
  const breadth = useMemo(() => computeBreadthStats(rows), [rows]);

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
      />

      <ScreenerStatsBar stats={breadth} total={totalCount} />

      {effectiveMode === 'table'
        ? <ScreenerTable rows={filteredRows} sortCol={sortCol} sortAsc={sortAsc} onSort={sortBy} loading={loading} hasMore={hasMore} onLoadMore={loadMore} onChart={setDetailSymbol} marketOpen={marketOpen} />
        : <ScreenerCards rows={filteredRows} loading={loading} hasMore={hasMore} onLoadMore={loadMore} onChart={setDetailSymbol} marketOpen={marketOpen} />
      }

      {detailSymbol && (
        <SymbolModal symbol={detailSymbol} initialTab="chart" onClose={() => setDetailSymbol(null)} />
      )}
    </div>
  );
}
