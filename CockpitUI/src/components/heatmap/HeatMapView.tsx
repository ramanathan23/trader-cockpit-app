'use client';

import { memo, useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import { EChart } from '@/components/charts/EChart';
import { useEChartColors } from '@/components/charts/useEChartColors';
import { HEAT_LEGEND, HEATMAP_MIN_ADV_CR, HEATMAP_TOP_PER_SIDE, heatStats, heatWeight, topLiquidMovers } from '@/lib/heatmap';
import type { HeatMapEntry } from '@/lib/heatmap';
import { fmt2 } from '@/lib/fmt';

interface HeatMapViewProps {
  entries:     HeatMapEntry[];
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

  const option = useMemo<EChartsOption>(() => ({
    backgroundColor: 'transparent',
    animationDuration: 260,
    tooltip: {
      trigger: 'item',
      borderColor: colors.border,
      backgroundColor: colors.panel,
      textStyle: { color: colors.fg, fontFamily: 'JetBrains Mono, Fira Code, monospace', fontSize: 11 },
      formatter: params => {
        const item = Array.isArray(params) ? params[0] : params;
        const data = (item as { data?: HeatMapEntry & { value: number } }).data;
        if (!data) return '';
        const move = data.chgPct == null ? '-' : `${data.chgPct > 0 ? '+' : ''}${data.chgPct.toFixed(2)}%`;
        const price = data.price == null ? '-' : fmt2(data.price);
        const score = data.score == null ? '-' : data.score.toFixed(0);
        return `<b>${data.symbol}</b><br/>Move: ${move}<br/>Price: ${price}<br/>Score: ${score}<br/>ADV: ${fmt2(data.adv)}Cr`;
      },
    },
    series: [{
      type: 'treemap',
      roam: false,
      nodeClick: false,
      breadcrumb: { show: false },
      left: 12,
      top: 12,
      right: 12,
      bottom: 12,
      squareRatio: 1.2,
      itemStyle: {
        borderColor: 'rgba(0,0,0,0.18)',
        borderWidth: 1,
        gapWidth: 3,
      },
      label: {
        show: true,
        color: '#fff',
        lineHeight: 14,
        fontFamily: 'JetBrains Mono, Fira Code, monospace',
        formatter: params => {
          const data = params.data as HeatMapEntry | undefined;
          if (!data) return '';
          const move = data.chgPct == null ? '-' : `${data.chgPct > 0 ? '+' : ''}${data.chgPct.toFixed(2)}%`;
          const price = data.price == null ? '' : `\n${fmt2(data.price)}`;
          return `{sym|${data.symbol}}\n{move|${move}}${price}`;
        },
        rich: {
          sym: { fontSize: 11, fontWeight: 900 },
          move: { fontSize: 11, fontWeight: 900 },
        },
      },
      upperLabel: { show: false },
      emphasis: {
        focus: 'self',
        itemStyle: { borderColor: 'rgba(255,255,255,0.55)', borderWidth: 1 },
      },
      data: visibleEntries.map(entry => ({
        ...entry,
        name: entry.symbol,
        value: heatWeight(entry.chgPct),
        itemStyle: { color: heatColor(entry.chgPct) },
      })),
    }],
  }), [colors, visibleEntries]);

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-base">
      <div className="shrink-0 border-b border-border bg-panel/90 px-4 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="mr-1">
            <div className="label-xs">Top Movers</div>
            <div className="num text-[18px] font-black leading-tight text-fg">{visibleEntries.length}</div>
          </div>
          <Metric label="Gainers" value={stats.gainers} tone="text-bull" />
          <Metric label="Losers" value={stats.losers} tone="text-bear" />
          <Metric label="Flat" value={stats.flat} tone="text-dim" />
          <Metric label="Avg" value={avg == null ? '-' : `${avg > 0 ? '+' : ''}${avg.toFixed(2)}%`} tone={avg == null ? 'text-dim' : avg >= 0 ? 'text-bull' : 'text-bear'} />
          <Metric label="Min ADV" value={`${HEATMAP_MIN_ADV_CR}Cr`} tone="text-dim" />
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-bold text-ghost">{HEATMAP_TOP_PER_SIDE}+{HEATMAP_TOP_PER_SIDE}</span>
            {HEAT_LEGEND.map(l => (
              <span key={l.label} className="flex items-center gap-1 text-[10px] font-bold text-dim">
                <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: l.color }} />
                {l.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="relative min-h-[360px] flex-1 overflow-hidden">
        {visibleEntries.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-[12px] text-ghost">No liquid movers</div>
        ) : (
          <EChart
            option={option}
            className="absolute inset-0"
            onClick={params => {
              const data = (params as { data?: HeatMapEntry }).data;
              if (data?.symbol) onCellClick(data.symbol);
            }}
          />
        )}
      </div>
    </div>
  );
}

function heatColor(pct: number | null): string {
  if (pct == null) return '#1f252a';
  if (pct > 5) return '#00a972';
  if (pct > 3) return '#078d67';
  if (pct > 1.5) return '#16775f';
  if (pct > 0.5) return '#2f665a';
  if (pct > -0.5) return '#879295';
  if (pct > -1.5) return '#8b5d66';
  if (pct > -3) return '#a84d5d';
  if (pct > -5) return '#bf4055';
  return '#d73751';
}

function Metric({ label, value, tone }: { label: string; value: number | string; tone: string }) {
  return (
    <div className="min-w-[64px] border-l border-border/80 pl-3">
      <div className="label-xs">{label}</div>
      <div className={`num text-[14px] font-black leading-tight ${tone}`}>{value}</div>
    </div>
  );
}
