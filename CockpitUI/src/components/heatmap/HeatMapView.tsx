'use client';

import { memo, useMemo } from 'react';
import { EChart } from '@/components/charts/EChart';
import { useEChartColors } from '@/components/charts/useEChartColors';
import { HEAT_LEGEND, HEATMAP_MIN_ADV_CR, HEATMAP_TOP_PER_SIDE, heatStats, topLiquidMovers } from '@/lib/heatmap';
import type { HeatMapEntry } from '@/lib/heatmap';
import { heatMapOption } from './heatMapOption';

interface HeatMapViewProps {
  entries: HeatMapEntry[];
  onCellClick: (symbol: string) => void;
}

export const HeatMapView = memo(({ entries, onCellClick }: HeatMapViewProps) => (
  <HeatMapFrame entries={entries} onCellClick={onCellClick} />
));
HeatMapView.displayName = 'HeatMapView';

function HeatMapFrame({ entries, onCellClick }: HeatMapViewProps) {
  const visibleEntries = useMemo(() => topLiquidMovers(entries), [entries]);
  const colors = useEChartColors();
  const stats = heatStats(visibleEntries);
  const avg = stats.avgMove;
  const option = useMemo(() => heatMapOption(visibleEntries, colors), [colors, visibleEntries]);

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-base">
      <HeatMapHeader stats={stats} avg={avg} />
      <div className="relative min-h-[360px] flex-1 overflow-hidden">
        {visibleEntries.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-[12px] text-ghost">No liquid movers</div>
        ) : (
          <EChart option={option} className="absolute inset-0" onClick={params => {
            const data = (params as { data?: HeatMapEntry }).data;
            if (data?.symbol) onCellClick(data.symbol);
          }} />
        )}
      </div>
    </div>
  );
}

function HeatMapHeader({ stats, avg }: { stats: ReturnType<typeof heatStats>; avg: number | null }) {
  return (
    <div className="shrink-0 border-b border-border bg-panel/90 px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="mr-1"><div className="label-xs">Top Movers</div><div className="num text-[18px] font-black leading-tight text-fg">{stats.gainers + stats.losers + stats.flat}</div></div>
        <Metric label="Gainers" value={stats.gainers} tone="text-bull" />
        <Metric label="Losers" value={stats.losers} tone="text-bear" />
        <Metric label="Flat" value={stats.flat} tone="text-dim" />
        <Metric label="Avg" value={avg == null ? '-' : `${avg > 0 ? '+' : ''}${avg.toFixed(2)}%`} tone={avg == null ? 'text-dim' : avg >= 0 ? 'text-bull' : 'text-bear'} />
        <Metric label="Min ADV" value={`${HEATMAP_MIN_ADV_CR}Cr`} tone="text-dim" />
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-bold text-ghost">{HEATMAP_TOP_PER_SIDE}+{HEATMAP_TOP_PER_SIDE}</span>
          {HEAT_LEGEND.map(l => <span key={l.label} className="flex items-center gap-1 text-[10px] font-bold text-dim"><span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: l.color }} />{l.label}</span>)}
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: number | string; tone: string }) {
  return (
    <div className="min-w-[64px] border-l border-border/80 pl-3">
      <div className="label-xs">{label}</div>
      <div className={`num text-[14px] font-black leading-tight ${tone}`}>{value}</div>
    </div>
  );
}

