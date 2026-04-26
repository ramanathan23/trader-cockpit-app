import type { EChartsOption } from 'echarts';
import type { EChartColors } from '@/components/charts/useEChartColors';
import type { ScoredSymbol } from '@/domain/dashboard';
import { dotJitter, dotRadius, QUAD_COMFORT, QUAD_TOTAL } from '@/lib/clusterUtils';

export function clusterChartOption(plotable: ScoredSymbol[], colors: EChartColors): EChartsOption {
  return {
    backgroundColor: 'transparent',
    animationDuration: 220,
    grid: { left: 58, right: 28, top: 32, bottom: 54 },
    tooltip: tooltip(colors),
    toolbox: toolbox(colors),
    xAxis: axis('Total Score', 32, colors),
    yAxis: axis('Comfort Score', 40, colors),
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, yAxisIndex: 0, filterMode: 'none' },
      { type: 'slider', xAxisIndex: 0, bottom: 20, height: 16, showDataShadow: false, borderColor: colors.border, fillerColor: `${colors.accent}33`, textStyle: { color: colors.ghost } },
    ],
    series: [{
      type: 'scatter',
      data: plotable.map(row => point(row, colors)),
      markLine: {
        symbol: 'none',
        silent: true,
        label: { color: colors.ghost, fontSize: 9, fontFamily: 'JetBrains Mono, Fira Code, monospace' },
        lineStyle: { color: colors.accent, type: 'dashed', opacity: 0.28 },
        data: [{ xAxis: QUAD_TOTAL, label: { formatter: 'Sweet spot' } }, { yAxis: QUAD_COMFORT, label: { formatter: 'High comfort' } }],
      },
    }],
  };
}

function tooltip(colors: EChartColors) {
  return {
    trigger: 'item' as const,
    borderColor: colors.border,
    backgroundColor: colors.panel,
    textStyle: { color: colors.fg, fontFamily: 'JetBrains Mono, Fira Code, monospace', fontSize: 11 },
    formatter: (params: unknown) => {
      const item = Array.isArray(params) ? params[0] : params;
      const row = ((item as { data?: { row?: ScoredSymbol } }).data)?.row;
      if (!row) return '';
      const comfort = row.comfort_score == null ? '-' : row.comfort_score.toFixed(0);
      return [`<b>${row.symbol}</b> <span style="color:${colors.ghost}">#${row.rank}</span>`, row.company_name ? `<span style="color:${colors.ghost}">${row.company_name}</span>` : '', `Total: ${row.total_score.toFixed(0)} | Comfort: ${comfort}`, `Mom: ${row.momentum_score.toFixed(0)} | Trend: ${row.trend_score.toFixed(0)}`, `RSI: ${row.rsi_14?.toFixed(0) ?? '-'} | ADX: ${row.adx_14?.toFixed(0) ?? '-'}`, `Bias: ${row.weekly_bias ?? 'NEUTRAL'}`].filter(Boolean).join('<br/>');
    },
  };
}

function toolbox(colors: EChartColors) {
  return {
    right: 8, top: 4, itemSize: 13,
    iconStyle: { borderColor: colors.dim },
    emphasis: { iconStyle: { borderColor: colors.fg } },
    feature: { dataZoom: { yAxisIndex: 'none' as const, title: { zoom: 'Box zoom', back: 'Zoom back' } }, restore: { title: 'Fit' } },
  };
}

function axis(name: string, nameGap: number, colors: EChartColors) {
  return {
    name, nameLocation: 'middle' as const, nameGap,
    min: (value: { min: number }) => Math.max(0, Math.floor(value.min - 4)),
    max: (value: { max: number }) => Math.min(100, Math.ceil(value.max + 4)),
    splitLine: { lineStyle: { color: colors.border, opacity: 0.55 } },
    axisLine: { lineStyle: { color: colors.border } },
    axisTick: { lineStyle: { color: colors.rim } },
    axisLabel: { color: colors.ghost, fontFamily: 'JetBrains Mono, Fira Code, monospace' },
    nameTextStyle: { color: colors.dim, fontFamily: 'JetBrains Mono, Fira Code, monospace', fontSize: 11 },
  };
}

function point(row: ScoredSymbol, colors: EChartColors) {
  const jitter = dotJitter(row.symbol);
  const color = dotColor(row, colors);
  return {
    name: row.symbol,
    value: [row.total_score + jitter.dx / 12, (row.comfort_score ?? 0) + jitter.dy / 12],
    row,
    symbolSize: dotRadius(row.total_score) * 2.4,
    itemStyle: { color, opacity: 0.72 },
    label: { show: row.total_score >= 76, formatter: row.symbol, position: 'right' as const, color, fontSize: 9, fontWeight: 800, fontFamily: 'JetBrains Mono, Fira Code, monospace' },
  };
}

function dotColor(row: ScoredSymbol, colors: EChartColors): string {
  if (row.weekly_bias === 'BULLISH') return colors.bull;
  if (row.weekly_bias === 'BEARISH') return colors.bear;
  return colors.amber;
}
