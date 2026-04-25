'use client';

import { memo, useState, useMemo } from 'react';
import { filterSignals, signalShort } from '@/domain/signal';
import type { Signal, SignalCategory, SignalType } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { HeatMapEntry } from '@/lib/heatmap';
import { useLivePrices } from '@/hooks/useLivePrices';
import { SymbolModal } from '@/components/dashboard/SymbolModal';
import { HeatMapView } from '@/components/heatmap/HeatMapView';

interface LiveHeatMapViewProps {
  metricsCache: Record<string, InstrumentMetrics | null>;
  signals: Signal[];
  category: SignalCategory;
  subType?: SignalType | null;
  fnoOnly?: boolean;
  minAdvCr: number;
}

export const LiveHeatMapView = memo(({ metricsCache, signals, category, subType, fnoOnly, minAdvCr }: LiveHeatMapViewProps) => {
  const [modalSymbol, setModalSymbol] = useState<string | null>(null);

  const filteredSignals = useMemo(
    () => filterSignals(signals, category, minAdvCr, metricsCache, subType, fnoOnly),
    [signals, category, minAdvCr, metricsCache, subType, fnoOnly],
  );
  const liveSymbols = useMemo(() => [...new Set(filteredSignals.map(signal => signal.symbol))], [filteredSignals]);
  const livePrices = useLivePrices(liveSymbols, liveSymbols.length > 0);

  const entries = useMemo<HeatMapEntry[]>(() => {
    const latestBySymbol = new Map<string, Signal>();
    for (const signal of filteredSignals) {
      if (!latestBySymbol.has(signal.symbol)) latestBySymbol.set(signal.symbol, signal);
    }

    return [...latestBySymbol.values()]
      .map(signal => {
        const m = metricsCache[signal.symbol];
        const lp = livePrices[signal.symbol];
        const price = lp?.ltp ?? m?.current_price ?? m?.day_close ?? signal.price ?? null;
        const prev = lp?.prevClose ?? m?.prev_day_close ?? null;
        const chgPct = price != null && prev ? (price - prev) / prev * 100 : (m?.day_chg_pct ?? null);
        return {
          symbol: signal.symbol,
          adv:    m?.adv_20_cr || 1,
          chgPct,
          price,
          score:  signal.score,
          stage:  m?.stage ?? undefined,
          signal: signalShort(signal.signal_type),
        };
      })
      .sort((a, b) => {
        const move = Math.abs(b.chgPct ?? 0) - Math.abs(a.chgPct ?? 0);
        return move !== 0 ? move : (b.adv ?? 0) - (a.adv ?? 0);
      });
  }, [filteredSignals, livePrices, metricsCache]);

  const entriesFromCache = useMemo<HeatMapEntry[]>(() =>
    Object.values(metricsCache)
      .filter((m): m is InstrumentMetrics => m != null)
      .map(m => ({
        symbol: m.symbol,
        adv:    m.adv_20_cr || 1,
        chgPct: m.day_chg_pct ?? null,
        price:  m.current_price ?? m.day_close ?? null,
        stage:  m.stage ?? undefined,
      }))
      .sort((a, b) => (b.adv ?? 0) - (a.adv ?? 0)),
  [metricsCache]);

  return (
    <>
      <HeatMapView entries={entries.length ? entries : entriesFromCache} onCellClick={setModalSymbol} />
      {modalSymbol && (
        <SymbolModal symbol={modalSymbol} initialTab="chart" onClose={() => setModalSymbol(null)} />
      )}
    </>
  );
});
LiveHeatMapView.displayName = 'LiveHeatMapView';
