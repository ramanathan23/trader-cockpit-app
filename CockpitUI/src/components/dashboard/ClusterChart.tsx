'use client';

import { useMemo, useState } from 'react';
import type { ScoredSymbol } from '@/domain/dashboard';
import { EChart } from '@/components/charts/EChart';
import { useEChartColors } from '@/components/charts/useEChartColors';
import { SymbolModal } from './SymbolModal';
import { clusterChartOption } from './clusterChartOption';

interface ClusterChartProps { scores: ScoredSymbol[]; loading: boolean; }

const LEGEND_ITEMS = [
  ['rgb(var(--bull))', 'Bullish'],
  ['rgb(var(--bear))', 'Bearish'],
  ['rgb(var(--amber))', 'Neutral'],
] as const;

export function ClusterChart({ scores, loading }: ClusterChartProps) {
  const colors = useEChartColors();
  const [selected, setSelected] = useState<string | null>(null);
  const plotable = useMemo(() => scores.filter(s => s.comfort_score != null), [scores]);
  const option = useMemo(() => clusterChartOption(plotable, colors), [colors, plotable]);

  if (loading) return <div className="flex flex-1 items-center justify-center text-[13px] text-dim">Computing cluster...</div>;

  return (
    <div className="relative flex flex-1 flex-col overflow-hidden">
      <EChart
        option={option}
        className="min-h-0 flex-1"
        onClick={params => {
          const row = (params as { data?: { row?: ScoredSymbol } }).data?.row;
          if (row?.symbol) setSelected(row.symbol);
        }}
      />
      {selected && <SymbolModal symbol={selected} initialTab="chart" onClose={() => setSelected(null)} />}
      <div className="flex shrink-0 items-center gap-4 border-t border-border bg-panel/80 px-4 py-2 text-[10px]">
        <span className="font-black uppercase text-ghost">Legend</span>
        {LEGEND_ITEMS.map(([color, label]) => (
          <span key={label} className="flex items-center gap-1.5">
            <svg width={10} height={10}><circle cx={5} cy={5} r={4} fill={color} fillOpacity={0.7} /></svg>
            <span className="text-ghost">{label}</span>
          </span>
        ))}
        <span className="text-ghost">- dot size = total score - wheel/box to zoom - drag slider to focus - click dot for chart</span>
        <span className="ml-auto num text-ghost">{plotable.length} plotted</span>
      </div>
    </div>
  );
}

