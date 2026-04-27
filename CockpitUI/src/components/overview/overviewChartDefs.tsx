'use client';

import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { Signal } from '@/domain/signal';
import type { StockRow } from '@/domain/stocklist';
import type { LivePriceData } from '@/components/ui/LivePrice';
import { HeatMapView } from '@/components/heatmap/HeatMapView';
import type { HeatMapEntry } from '@/lib/heatmap';
import { BreadthBars } from './BreadthBars';
import { MomentumTrendMatrix } from './MomentumTrendMatrix';
import { ScoreHistogram } from './ScoreHistogram';
import { SignalFlowChart } from './SignalFlowChart';
import { TopSetups } from './TopSetups';

export type ChartKey = 'heat' | 'score' | 'matrix' | 'flow' | 'breadth' | 'setups';
export type ChartRenderMode = 'body' | 'dock' | 'expand';

interface DefProps {
  rows: StockRow[];
  heatEntries: HeatMapEntry[];
  loading: boolean;
  signals: Signal[];
  metricsCache: Record<string, InstrumentMetrics | null>;
  livePrices: Record<string, LivePriceData>;
  onSymbol: (symbol: string) => void;
}

export function chartDefs(p: DefProps) {
  return [
    def('heat', 'Top Movers', 'Liquid gainers and losers', 'xl:col-span-5',
      'flex h-[460px] min-h-0', 'flex h-[620px] min-h-0', 'flex min-h-0 flex-1',
      () => <HeatMapView entries={p.heatEntries} onCellClick={p.onSymbol} />),
    def('score', 'Score Distribution', 'Where the universe is concentrated', 'xl:col-span-6',
      '', 'h-80', 'flex min-h-0 flex-1', mode => <ScoreHistogram rows={p.rows} className={chartHeight(mode)} />),
    def('matrix', 'Momentum / Trend Matrix', 'Breakouts, pullbacks, spikes, ignores', 'xl:col-span-6',
      '', 'h-80', 'flex min-h-0 flex-1', mode => <MomentumTrendMatrix rows={p.rows} onSymbol={p.onSymbol} className={chartHeight(mode)} />),
    def('flow', 'Signal Flow', 'Live tape mix by setup type', 'xl:col-span-6',
      '', 'h-80', 'flex min-h-0 flex-1', mode => <SignalFlowChart signals={p.signals} metricsCache={p.metricsCache} expanded={mode === 'expand'} />),
    def('breadth', 'Breadth', 'Bias and setup quality', 'xl:col-span-6',
      '', 'h-80', 'flex min-h-0 flex-1', mode => <BreadthBars rows={p.rows} className={chartHeight(mode)} />),
    def('setups', 'Top Setups', 'Highest attention candidates', 'xl:col-span-12',
      '', '', '', () => <TopSetups rows={p.rows.slice(0, 12)} livePrices={p.livePrices} signals={p.signals} onSymbol={p.onSymbol} />),
  ];
}

function def(
  id: ChartKey,
  title: string,
  caption: string,
  className: string,
  bodyClassName: string,
  dockClassName: string,
  expandClassName: string,
  render: (mode: ChartRenderMode) => React.ReactNode,
) {
  return { id, title, caption, className, bodyClassName, dockClassName, expandClassName, render };
}

function chartHeight(mode: ChartRenderMode): string {
  return mode === 'expand' ? 'h-full min-h-0 w-full' : 'h-64 w-full';
}
