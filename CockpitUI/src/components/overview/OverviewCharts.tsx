'use client';

import { useMemo, useState } from 'react';
import type { ScoredSymbol } from '@/domain/dashboard';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { Signal } from '@/domain/signal';
import type { StockRow } from '@/domain/stocklist';
import type { LivePriceData } from '@/components/ui/LivePrice';
import type { HeatMapEntry } from '@/lib/heatmap';
import { OverviewChartPanel, ExpandedChart } from './OverviewChartPanel';
import { chartDefs, type ChartKey } from './overviewChartDefs';

export function OverviewCharts(props: {
  rows: StockRow[];
  heatEntries: HeatMapEntry[];
  scored: ScoredSymbol[];
  loading: boolean;
  signals: Signal[];
  metricsCache: Record<string, InstrumentMetrics | null>;
  livePrices: Record<string, LivePriceData>;
  onSymbol: (symbol: string) => void;
}) {
  const [docked, setDocked] = useState<ChartKey | null>(null);
  const [expanded, setExpanded] = useState<ChartKey | null>(null);
  const defs = useMemo(() => chartDefs(props), [props]);
  const dockedDef = docked ? defs.find(def => def.id === docked) : null;
  const expandedDef = expanded ? defs.find(def => def.id === expanded) : null;

  return (
    <>
      <div className="grid gap-3 p-3 xl:grid-cols-12">
        {dockedDef && (
          <ChartPanel def={dockedDef} docked={docked === dockedDef.id}
            className="xl:col-span-12" onDock={setDocked} onExpand={setExpanded} />
        )}
        {defs.filter(def => def.id !== docked).map(def => (
          <ChartPanel key={def.id} def={def} docked={false}
            onDock={setDocked} onExpand={setExpanded} />
        ))}
      </div>
      {expandedDef && (
        <ExpandedChart title={expandedDef.title} onClose={() => setExpanded(null)}>
          <div className={expandedDef.expandClassName}>{expandedDef.render('expand')}</div>
        </ExpandedChart>
      )}
    </>
  );
}

function ChartPanel({
  def, docked, className, onDock, onExpand,
}: {
  def: ReturnType<typeof chartDefs>[number];
  docked: boolean;
  className?: string;
  onDock: (id: ChartKey | null) => void;
  onExpand: (id: ChartKey) => void;
}) {
  return (
    <OverviewChartPanel id={def.id} title={def.title} caption={def.caption}
      className={className ?? def.className} docked={docked} onDock={onDock} onExpand={onExpand}>
      <div className={docked ? def.dockClassName : def.bodyClassName}>{def.render(docked ? 'dock' : 'body')}</div>
    </OverviewChartPanel>
  );
}
