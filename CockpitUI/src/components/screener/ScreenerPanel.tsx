'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useScreener } from '@/hooks/useScreener';
import { computeBreadthStats } from '@/domain/screener';
import { ScreenerFilters } from './ScreenerFilters';
import { ScreenerTable } from './ScreenerTable';
import { ScreenerCards } from './ScreenerCards';
import { ScreenerStatsBar } from './ScreenerStatsBar';
import { DailyChart } from '@/components/dashboard/DailyChart';
import { OptionChainPanel } from '@/components/dashboard/OptionChainPanel';

interface ScreenerPanelProps {
  active: boolean;
}

export function ScreenerPanel({ active }: ScreenerPanelProps) {
  const [viewMode, setViewMode] = useState<'card' | 'table'>('table');
  const [chartSymbol, setChartSymbol] = useState<string | null>(null);
  const [ocSymbol,    setOcSymbol]    = useState<string | null>(null);

  const {
    rows, filteredRows, loading, hasMore,
    query, setQuery,
    range, setRange,
    presets, togglePreset,
    fnoOnly, setFnoOnly,
    sortCol, sortAsc, sortBy,
    loadScreener, loadMore, resetFilters,
    totalCount, apiTotal,
  } = useScreener();

  const breadth = useMemo(() => computeBreadthStats(rows), [rows]);

  // Auto-load on first activation
  useEffect(() => {
    if (active && totalCount === 0 && !loading) {
      loadScreener();
    }
  }, [active]); // eslint-disable-line react-hooks/exhaustive-deps

  // Background auto-load all pages so breadth stats cover full universe
  useEffect(() => {
    if (!loading && hasMore) loadMore();
  }, [rows.length, loading, hasMore]); // eslint-disable-line react-hooks/exhaustive-deps

  const openChart = useCallback((sym: string) => setChartSymbol(sym), []);
  const openOC    = useCallback((sym: string) => setOcSymbol(sym), []);

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

      <ScreenerStatsBar stats={breadth} total={apiTotal || rows.length} />

      {viewMode === 'table'
        ? <ScreenerTable rows={filteredRows} sortCol={sortCol} sortAsc={sortAsc} onSort={sortBy}
            loading={loading} hasMore={hasMore} onLoadMore={loadMore}
            onChart={openChart} onOptionChain={openOC} />
        : <ScreenerCards rows={filteredRows} loading={loading} hasMore={hasMore} onLoadMore={loadMore}
            onChart={openChart} onOptionChain={openOC} />
      }

      {/* Chart modal */}
      {chartSymbol && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setChartSymbol(null)}
        >
          <div
            className="bg-panel border border-border rounded-lg shadow-2xl overflow-hidden"
            style={{ width: 900, maxWidth: '95vw' }}
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="font-bold text-fg">{chartSymbol}</span>
                {rows.find(r => r.symbol === chartSymbol)?.is_fno && (
                  <span className="text-[7px] font-black px-1 py-0.5 rounded-sm"
                        style={{ background: '#9b72f718', color: '#9b72f7' }}>F&amp;O</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {rows.find(r => r.symbol === chartSymbol)?.is_fno && (
                  <button
                    onClick={() => { setChartSymbol(null); setOcSymbol(chartSymbol); }}
                    className="text-[10px] font-bold text-accent hover:text-fg transition-colors px-2 py-1 border border-accent/40 rounded-sm"
                  >OC</button>
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
      {ocSymbol && (
        <OptionChainPanel
          symbol={ocSymbol}
          onClose={() => setOcSymbol(null)}
          scoreData={null}
        />
      )}
    </div>
  );
}
