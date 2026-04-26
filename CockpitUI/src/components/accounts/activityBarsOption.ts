import type { EChartsOption } from 'echarts';
import type { EChartColors } from '@/components/charts/useEChartColors';
import type { Dashboard } from './accountTypes';

type DailyRow = Dashboard['daily'][number];

export function activityBarsOption(
  rows: DailyRow[],
  maxTrades: number,
  colors: EChartColors,
): EChartsOption {
  return {
    backgroundColor: 'transparent',
    color: [colors.accent, colors.bull, colors.bear],
    grid: { left: 42, right: 18, top: 18, bottom: 26 },
    tooltip: {
      trigger: 'axis',
      borderColor: colors.border,
      backgroundColor: colors.panel,
      textStyle: { color: colors.fg, fontFamily: 'JetBrains Mono, Fira Code, monospace', fontSize: 11 },
      formatter: params => {
        const items = Array.isArray(params) ? params : [params];
        const idx = (items[0] as { dataIndex?: number } | undefined)?.dataIndex ?? 0;
        const row = rows[idx];
        if (!row) return '';
        return [
          `<b>${row.date}</b>`,
          `Trades: ${row.trades ?? 0}`,
          `Wins: ${row.wins ?? 0} (${row.win_pct ?? 0}%)`,
          `Losses: ${row.losses ?? 0} (${row.loss_pct ?? 0}%)`,
          `Fills: ${row.executions}`,
        ].join('<br/>');
      },
    },
    legend: { show: false },
    xAxis: {
      type: 'category',
      data: rows.map(row => row.date.slice(8, 10)),
      boundaryGap: false,
      axisLine: { lineStyle: { color: colors.border } },
      axisTick: { show: false },
      axisLabel: { color: colors.ghost, fontFamily: 'JetBrains Mono, Fira Code, monospace', fontSize: 9 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitNumber: 2,
      axisLabel: { color: colors.ghost, fontFamily: 'JetBrains Mono, Fira Code, monospace', fontSize: 9 },
      splitLine: { lineStyle: { color: colors.border, opacity: 0.6 } },
    },
    series: [
      line('Trades', rows.map(row => ((row.trades ?? 0) / maxTrades) * 100)),
      line('Win %', rows.map(row => row.win_pct ?? 0)),
      line('Loss %', rows.map(row => row.loss_pct ?? 0)),
    ],
  };
}

function line(name: string, data: number[]) {
  return {
    name,
    type: 'line' as const,
    smooth: true,
    symbolSize: 4,
    lineStyle: { width: 2.2 },
    data,
  };
}
