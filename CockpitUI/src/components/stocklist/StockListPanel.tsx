'use client';

import { memo, useEffect, useMemo } from 'react';
import { useStockList } from '@/hooks/useStockList';
import { useLivePrices } from '@/hooks/useLivePrices';
import type { NoteEntry } from '@/hooks/useNotes';
import { SymbolModal } from '@/components/dashboard/SymbolModal';
import { StockListFilters } from './StockListFilters';
import { StockListTable } from './StockListTable';
import { StockListCardView } from './StockListCardView';
import { StockListChartView } from './StockListChartView';
import { StockListClusterView } from './StockListClusterView';
import { StockListHeatMapView } from './StockListHeatMapView';
import { useStockListState } from './useStockListState';

interface StockListPanelProps {
  active:       boolean;
  noteEntries:  Record<string, NoteEntry[]>;
  onAddNote:    (symbol: string, text: string) => void;
  onDeleteNote: (symbol: string, id: string)   => void;
}

export const StockListPanel = memo(({
  active, noteEntries, onAddNote, onDeleteNote,
}: StockListPanelProps) => {
  const list  = useStockList(noteEntries);
  const state = useStockListState();

  useEffect(() => {
    if (active && !list.fetched) list.load();
  }, [active]); // eslint-disable-line react-hooks/exhaustive-deps

  const symbols    = useMemo(() => list.rows.map(r => r.symbol), [list.rows]);
  const livePrices = useLivePrices(symbols, active);
  const modalRow   = state.modalSymbol ? list.rows.find(r => r.symbol === state.modalSymbol) : undefined;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <StockListFilters
        query={list.query}           fnoOnly={list.fnoOnly}
        presets={list.presets}       showPresets={state.showPresets}
        loading={list.loading}       totalCount={list.totalCount}
        filteredCount={list.filteredRows.length}
        viewMode={state.viewMode}
        onQuery={list.setQuery}      onFnoOnly={list.setFnoOnly}
        onPreset={list.togglePreset} onReset={list.resetFilters}
        onRefresh={list.load}        onShowPresets={state.setShowPresets}
        onViewMode={state.setViewMode}
      />

      {state.viewMode === 'table' && (
        <StockListTable
          rows={list.filteredRows}       expandedSymbol={state.expandedSymbol}
          livePrices={livePrices}        noteEntries={noteEntries}
          sortCol={list.sortCol}         sortAsc={list.sortAsc}
          onSort={list.sortBy}           onToggle={state.toggleExpand}
          onOpenModal={state.openModal}  onAddNote={onAddNote}
          onDeleteNote={onDeleteNote}
          loading={list.loading}          hasMore={list.hasMore}
          onLoadMore={list.loadMore}
        />
      )}

      {state.viewMode === 'card' && (
        <StockListCardView
          rows={list.filteredRows}
          livePrices={livePrices}
          noteEntries={noteEntries}
          onOpenModal={state.openModal}
          loading={list.loading}
          hasMore={list.hasMore}
          onLoadMore={list.loadMore}
        />
      )}

      {state.viewMode === 'chart' && (
        <StockListChartView rows={list.filteredRows} livePrices={livePrices}
          loading={list.loading} hasMore={list.hasMore} onLoadMore={list.loadMore} />
      )}

      {state.viewMode === 'cluster' && (
        <StockListClusterView rows={list.filteredRows} loading={list.loading} />
      )}

      {state.viewMode === 'heatmap' && (
        <StockListHeatMapView rows={list.filteredRows} livePrices={livePrices} />
      )}

      {state.modalSymbol && (
        <SymbolModal
          symbol={state.modalSymbol}
          row={modalRow}
          initialTab={state.modalTab}
          onClose={state.closeModal}
          noteEntries={noteEntries[state.modalSymbol] ?? []}
          onAddNote={onAddNote}
          onDeleteNote={onDeleteNote}
        />
      )}
    </div>
  );
});
StockListPanel.displayName = 'StockListPanel';
