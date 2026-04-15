'use client';

import { useEffect, useState } from 'react';
import { useScreener } from '@/hooks/useScreener';
import { ScreenerFilters } from './ScreenerFilters';
import { ScreenerTable } from './ScreenerTable';
import { ScreenerCards } from './ScreenerCards';

interface ScreenerPanelProps {
  active: boolean;
}

export function ScreenerPanel({ active }: ScreenerPanelProps) {
  const [viewMode, setViewMode] = useState<'card' | 'table'>('table');

  const {
    filteredRows, loading,
    query, setQuery,
    range, setRange,
    presets, togglePreset,
    sortCol, sortAsc, sortBy,
    loadScreener, resetFilters,
    totalCount,
  } = useScreener();

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
        onReset={resetFilters}
        totalCount={totalCount}  filteredCount={filteredRows.length}
        loading={loading}        onRefresh={loadScreener}
        viewMode={viewMode}      onViewMode={setViewMode}
      />

      {viewMode === 'table'
        ? <ScreenerTable rows={filteredRows} sortCol={sortCol} sortAsc={sortAsc} onSort={sortBy} loading={loading} />
        : <ScreenerCards rows={filteredRows} loading={loading} />
      }
    </div>
  );
}
