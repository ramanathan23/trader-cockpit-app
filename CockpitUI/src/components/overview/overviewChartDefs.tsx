'use client';

import type { ScoredSymbol } from '@/domain/dashboard';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { Signal } from '@/domain/signal';
import type { StockRow } from '@/domain/stocklist';
import type { LivePriceData } from '@/components/ui/LivePrice';
import { ClusterChart } from '@/components/dashboard/ClusterChart';
import { HeatMapView } from '@/components/heatmap/HeatMapView';
import type { HeatMapEntry } from '@/lib/heatmap';
import { BreadthBars } from './BreadthBars';
import { MomentumTrendMatrix } from './MomentumTrendMatrix';
import { ScoreHistogram } from './ScoreHistogram';
import { SignalFlowChart } from './SignalFlowChart';
import { TopSetups } from './TopSetups';

export type ChartKey = 'heat' | 'cluster' | 'score' | 'matrix' | 'flow' | 'breadth' | 'setups';

interface DefProps {
  rows: StockRow[];
  heatEntries: HeatMapEntry[];
  scored: ScoredSymbol[];
  loading: boolean;
  signals: Signal[];
  metricsCache: Record<string, InstrumentMetrics | null>;
  livePrices: Record<string, LivePriceData>;
  onSymbol: (symbol: string) => void;
}

export function chartDefs(p: DefProps) {
  return [
    def('heat', 'Top Movers', 'Liquid gainers and losers', 'xl:col-span-5',
      'h-[460px] min-h-0', 'h-[620px] min-h-0', 'h-full min-h-[720px]',
      () => <HeatMapView entries={p.heatEntries} onCellClick={p.onSymbol} />),
    def('cluster', 'Opportunity Cluster', 'Total score vs comfort', 'xl:col-span-7',
      'flex h-[460px] min-h-0', 'flex h-[620px] min-h-0', 'flex h-full min-h-[720px]',
      () => <ClusterChart scores={p.scored} loading={p.loading} />),
    def('score', 'Score Distribution', 'Where the universe is concentrated', 'xl:col-span-4',
      '', 'h-80', 'h-full min-h-[620px]', () => <ScoreHistogram rows={p.rows} />),
    def('matrix', 'Momentum / Trend Matrix', 'Breakouts, pullbacks, spikes, ignores', 'xl:col-span-4',
      '', 'h-80', 'h-full min-h-[620px]', () => <MomentumTrendMatrix rows={p.rows} onSymbol={p.onSymbol} />),
    def('flow', 'Signal Flow', 'Live tape mix by setup type', 'xl:col-span-4',
      '', 'h-80', 'h-full min-h-[560px]', () => <SignalFlowChart signals={p.signals} metricsCache={p.metricsCache} />),
    def('breadth', 'Breadth', 'Bias and setup quality', 'xl:col-span-4',
      '', 'h-80', 'h-full min-h-[560px]', () => <BreadthBars rows={p.rows} />),
    def('setups', 'Top Setups', 'Highest attention candidates', 'xl:col-span-8',
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
  render: () => React.ReactNode,
) {
  return { id, title, caption, className, bodyClassName, dockClassName, expandClassName, render };
}

