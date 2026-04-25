'use client';

import { memo, useState, useMemo } from 'react';
import type { StockRow } from '@/domain/stocklist';
import type { LivePriceData } from '@/components/ui/LivePrice';
import type { HeatMapEntry } from '@/lib/heatmap';
import { SymbolModal } from '@/components/dashboard/SymbolModal';
import { HeatMapView } from '@/components/heatmap/HeatMapView';

interface StockListHeatMapViewProps {
  rows:       StockRow[];
  livePrices: Record<string, LivePriceData>;
}

function computeChgPct(lp: LivePriceData | undefined, row: StockRow): number | null {
  const ltp  = lp?.ltp ?? row.display_price ?? null;
  const prev = lp?.prevClose ?? row.prev_day_close ?? null;
  if (ltp == null || prev == null || prev === 0) return null;
  return (ltp - prev) / prev * 100;
}

export const StockListHeatMapView = memo(({ rows, livePrices }: StockListHeatMapViewProps) => {
  const [modalSymbol, setModalSymbol] = useState<string | null>(null);

  const entries = useMemo<HeatMapEntry[]>(() =>
    rows
      .map(row => ({
        symbol: row.symbol,
        adv:    row.adv_20_cr || 1,
        chgPct: computeChgPct(livePrices[row.symbol], row),
        score:  row.total_score ?? undefined,
      }))
      .sort((a, b) => (b.adv ?? 0) - (a.adv ?? 0)),
  [rows, livePrices]);

  return (
    <>
      <HeatMapView entries={entries} onCellClick={setModalSymbol} />
      {modalSymbol && (
        <SymbolModal symbol={modalSymbol} initialTab="chart" onClose={() => setModalSymbol(null)} />
      )}
    </>
  );
});
StockListHeatMapView.displayName = 'StockListHeatMapView';
