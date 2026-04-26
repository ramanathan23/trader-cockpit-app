import type { EChartsOption } from 'echarts';
import type { EChartColors } from '@/components/charts/useEChartColors';
import type { HeatMapEntry } from '@/lib/heatmap';
import { heatWeight } from '@/lib/heatmap';
import { fmt2 } from '@/lib/fmt';

export function heatMapOption(entries: HeatMapEntry[], colors: EChartColors): EChartsOption {
  return {
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
      itemStyle: { borderColor: 'rgba(0,0,0,0.18)', borderWidth: 1, gapWidth: 3 },
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
        rich: { sym: { fontSize: 11, fontWeight: 900 }, move: { fontSize: 11, fontWeight: 900 } },
      },
      upperLabel: { show: false },
      data: entries.map(entry => ({
        ...entry,
        name: entry.symbol,
        value: heatWeight(entry.chgPct),
        itemStyle: { color: heatColor(entry.chgPct) },
      })),
    }],
  };
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
