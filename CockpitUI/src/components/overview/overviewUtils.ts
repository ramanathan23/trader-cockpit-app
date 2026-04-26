import { signalShort } from '@/domain/signal';
import type { Signal } from '@/domain/signal';
import type { StockRow } from '@/domain/stocklist';
import type { LivePriceData } from '@/components/ui/LivePrice';
import { heatMoveSort, type HeatMapEntry } from '@/lib/heatmap';

export function computeChgPct(lp: LivePriceData | undefined, row: StockRow): number | null {
  const ltp = lp?.ltp ?? row.display_price ?? null;
  const prev = lp?.prevClose ?? row.prev_day_close ?? null;
  if (ltp == null || prev == null || prev === 0) return null;
  return (ltp - prev) / prev * 100;
}

export function latestSignalLabel(signals: Signal[], symbol: string): string | undefined {
  const signal = signals.find(item => item.symbol === symbol);
  return signal ? signalShort(signal.signal_type) : undefined;
}

export function rankedScoredRows(rows: StockRow[]): StockRow[] {
  return [...rows]
    .filter(row => row.total_score != null)
    .sort((a, b) => (b.total_score ?? 0) - (a.total_score ?? 0));
}

export function buildHeatEntries(
  rows: StockRow[],
  livePrices: Record<string, LivePriceData>,
  signals: Signal[],
): HeatMapEntry[] {
  return rows
    .map(row => ({
      symbol: row.symbol,
      adv: row.adv_20_cr || 1,
      chgPct: computeChgPct(livePrices[row.symbol], row),
      price: livePrices[row.symbol]?.ltp ?? row.display_price ?? null,
      score: row.total_score ?? undefined,
      stage: row.stage ?? undefined,
      signal: latestSignalLabel(signals, row.symbol),
    }))
    .sort(heatMoveSort);
}

