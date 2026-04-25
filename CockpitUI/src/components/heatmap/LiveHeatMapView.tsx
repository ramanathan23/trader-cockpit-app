'use client';

import { memo, useState, useMemo } from 'react';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { HeatMapEntry } from '@/lib/heatmap';
import { SymbolModal } from '@/components/dashboard/SymbolModal';
import { HeatMapView } from '@/components/heatmap/HeatMapView';

interface LiveHeatMapViewProps {
  metricsCache: Record<string, InstrumentMetrics | null>;
}

export const LiveHeatMapView = memo(({ metricsCache }: LiveHeatMapViewProps) => {
  const [modalSymbol, setModalSymbol] = useState<string | null>(null);

  const entries = useMemo<HeatMapEntry[]>(() =>
    Object.values(metricsCache)
      .filter((m): m is InstrumentMetrics => m != null)
      .map(m => ({
        symbol: m.symbol,
        adv:    m.adv_20_cr || 1,
        chgPct: m.day_chg_pct ?? null,
      }))
      .sort((a, b) => (b.adv ?? 0) - (a.adv ?? 0)),
  [metricsCache]);

  return (
    <>
      <HeatMapView entries={entries} onCellClick={setModalSymbol} />
      {modalSymbol && (
        <SymbolModal symbol={modalSymbol} initialTab="chart" onClose={() => setModalSymbol(null)} />
      )}
    </>
  );
});
LiveHeatMapView.displayName = 'LiveHeatMapView';
