'use client';

import { memo, useEffect, useMemo, useState } from 'react';
import type { ScoredSymbol } from '@/domain/dashboard';
import { useLivePrices } from '@/hooks/useLivePrices';
import { useStockList } from '@/hooks/useStockList';
import { SymbolModal } from '@/components/dashboard/SymbolModal';
import { OverviewHeader } from './OverviewShell';
import { OverviewCharts } from './OverviewCharts';
import type { OverviewDashboardProps } from './overviewTypes';
import { buildHeatEntries, rankedScoredRows } from './overviewUtils';

export const OverviewDashboard = memo(function OverviewDashboard({
  active, signals, metricsCache, marketOpen, noteEntries,
}: OverviewDashboardProps) {
  const list = useStockList(noteEntries);
  const [modalSymbol, setModalSymbol] = useState<string | null>(null);

  useEffect(() => {
    if (active && !list.fetched) list.load();
  }, [active]); // eslint-disable-line react-hooks/exhaustive-deps

  const rankedRows = useMemo(() => rankedScoredRows(list.rows), [list.rows]);
  const modalRow = useMemo(
    () => modalSymbol ? rankedRows.find(row => row.symbol === modalSymbol) : undefined,
    [modalSymbol, rankedRows],
  );
  const symbols = useMemo(() => rankedRows.slice(0, 120).map(row => row.symbol), [rankedRows]);
  const livePrices = useLivePrices(symbols, active);
  const heatEntries = useMemo(() => buildHeatEntries(rankedRows, livePrices, signals), [rankedRows, livePrices, signals]);
  const scored = useMemo(
    () => rankedRows.filter(row => row.total_score != null && row.comfort_score != null) as unknown as ScoredSymbol[],
    [rankedRows],
  );
  const highConviction = rankedRows.filter(row => (row.total_score ?? 0) >= 75).length;
  const fnoCount = rankedRows.filter(row => row.is_fno).length;
  const bullish = rankedRows.filter(row => row.weekly_bias === 'BULLISH').length;
  const bearish = rankedRows.filter(row => row.weekly_bias === 'BEARISH').length;

  return (
    <div className="min-h-0 flex-1 overflow-auto bg-base">
      <OverviewHeader loading={list.loading} count={rankedRows.length} marketOpen={marketOpen}
        signalCount={signals.length} highConviction={highConviction} fnoCount={fnoCount}
        bullish={bullish} bearish={bearish} />
      <OverviewCharts rows={rankedRows} heatEntries={heatEntries} scored={scored} loading={list.loading}
        signals={signals} metricsCache={metricsCache} livePrices={livePrices} onSymbol={setModalSymbol} />
      {modalSymbol && <SymbolModal symbol={modalSymbol} row={modalRow} initialTab="chart" onClose={() => setModalSymbol(null)} />}
    </div>
  );
});
