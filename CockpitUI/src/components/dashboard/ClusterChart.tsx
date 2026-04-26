'use client';

import { useMemo, useState } from 'react';
import type { EChartsOption } from 'echarts';
import type { ScoredSymbol } from '@/domain/dashboard';
import { EChart } from '@/components/charts/EChart';
import { useEChartColors } from '@/components/charts/useEChartColors';
import { dotColor, dotJitter, dotRadius, QUAD_COMFORT, QUAD_TOTAL } from '@/lib/clusterUtils';
import { SymbolModal } from './SymbolModal';

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

  const option = useMemo<EChartsOption>(() => ({
    backgroundColor: 'transparent',
    animationDuration: 220,
    grid: { left: 58, right: 28, top: 32, bottom: 54 },
    tooltip: {
      trigger: 'item',
      borderColor: colors.border,
      backgroundColor: colors.panel,
      textStyle: { color: colors.fg, fontFamily: 'JetBrains Mono, Fira Code, monospace', fontSize: 11 },
      formatter: params => {
        const item = Array.isArray(params) ? params[0] : params;
        const row = ((item as { data?: { row?: ScoredSymbol } }).data)?.row;
        if (!row) return '';
        const comfort = row.comfort_score == null ? '-' : row.comfort_score.toFixed(0);
        return [
          `<b>${row.symbol}</b> <span style="color:${colors.ghost}">#${row.rank}</span>`,
          row.company_name ? `<span style="color:${colors.ghost}">${row.company_name}</span>` : '',
          `Total: ${row.total_score.toFixed(0)} | Comfort: ${comfort}`,
          `Mom: ${row.momentum_score.toFixed(0)} | Trend: ${row.trend_score.toFixed(0)}`,
          `RSI: ${row.rsi_14?.toFixed(0) ?? '-'} | ADX: ${row.adx_14?.toFixed(0) ?? '-'}`,
          `Bias: ${row.weekly_bias ?? 'NEUTRAL'}`,
        ].filter(Boolean).join('<br/>');
      },
    },
    toolbox: {
      right: 8,
      top: 4,
      itemSize: 13,
      iconStyle: { borderColor: colors.dim },
      emphasis: { iconStyle: { borderColor: colors.fg } },
      feature: {
        dataZoom: { yAxisIndex: 'none', title: { zoom: 'Box zoom', back: 'Zoom back' } },
        restore: { title: 'Fit' },
      },
    },
    xAxis: {
      name: 'Total Score',
      nameLocation: 'middle',
      nameGap: 32,
      min: value => Math.max(0, Math.floor(value.min - 4)),
      max: value => Math.min(100, Math.ceil(value.max + 4)),
      splitLine: { lineStyle: { color: colors.border, opacity: 0.55 } },
      axisLine: { lineStyle: { color: colors.border } },
      axisTick: { lineStyle: { color: colors.rim } },
      axisLabel: { color: colors.ghost, fontFamily: 'JetBrains Mono, Fira Code, monospace' },
      nameTextStyle: { color: colors.dim, fontFamily: 'JetBrains Mono, Fira Code, monospace', fontSize: 11 },
    },
    yAxis: {
      name: 'Comfort Score',
      nameLocation: 'middle',
      nameGap: 40,
      min: value => Math.max(0, Math.floor(value.min - 4)),
      max: value => Math.min(100, Math.ceil(value.max + 4)),
      splitLine: { lineStyle: { color: colors.border, opacity: 0.55 } },
      axisLine: { lineStyle: { color: colors.border } },
      axisTick: { lineStyle: { color: colors.rim } },
      axisLabel: { color: colors.ghost, fontFamily: 'JetBrains Mono, Fira Code, monospace' },
      nameTextStyle: { color: colors.dim, fontFamily: 'JetBrains Mono, Fira Code, monospace', fontSize: 11 },
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, yAxisIndex: 0, filterMode: 'none' },
      { type: 'slider', xAxisIndex: 0, bottom: 20, height: 16, showDataShadow: false, borderColor: colors.border, fillerColor: `${colors.accent}33`, textStyle: { color: colors.ghost } },
    ],
    series: [{
      type: 'scatter',
      data: plotable.map(row => {
        const jitter = dotJitter(row.symbol);
        return {
          name: row.symbol,
          value: [row.total_score + jitter.dx / 12, (row.comfort_score ?? 0) + jitter.dy / 12],
          row,
          symbolSize: dotRadius(row.total_score) * 2.4,
          itemStyle: { color: dotColor(row), opacity: 0.58 },
          label: {
            show: row.total_score >= 76,
            formatter: row.symbol,
            position: 'right',
            color: dotColor(row),
            fontSize: 9,
            fontWeight: 800,
            fontFamily: 'JetBrains Mono, Fira Code, monospace',
          },
        };
      }),
      emphasis: {
        focus: 'self',
        scale: 1.5,
        itemStyle: { opacity: 0.92, borderWidth: 2 },
        label: { show: true },
      },
      markLine: {
        symbol: 'none',
        silent: true,
        label: { color: colors.ghost, fontSize: 9, fontFamily: 'JetBrains Mono, Fira Code, monospace' },
        lineStyle: { color: colors.accent, type: 'dashed', opacity: 0.28 },
        data: [
          { xAxis: QUAD_TOTAL, label: { formatter: 'Sweet spot' } },
          { yAxis: QUAD_COMFORT, label: { formatter: 'High comfort' } },
        ],
      },
    }],
  }), [colors, plotable]);

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
