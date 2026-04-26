'use client';

import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import { EChart } from '@/components/charts/EChart';
import { useEChartColors } from '@/components/charts/useEChartColors';
import type { RowsProps } from './overviewTypes';

export function BreadthBars({ rows, className = 'h-64 w-full' }: RowsProps & { className?: string }) {
  const colors = useEChartColors();
  const stats = useMemo(() => [
    { label: 'Bullish', value: rows.filter(r => r.weekly_bias === 'BULLISH').length, color: colors.bull },
    { label: 'Bearish', value: rows.filter(r => r.weekly_bias === 'BEARISH').length, color: colors.bear },
    { label: 'Stage 2', value: rows.filter(r => r.stage === 'STAGE_2' || r.stage === '2').length, color: colors.accent },
    { label: 'Squeeze', value: rows.filter(r => r.bb_squeeze).length, color: colors.sky },
    { label: 'NR7', value: rows.filter(r => r.nr7).length, color: colors.amber },
  ], [colors, rows]);
  const option = useMemo<EChartsOption>(() => ({
    backgroundColor: 'transparent',
    grid: { left: 70, right: 12, top: 18, bottom: 22 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, borderColor: colors.border, backgroundColor: colors.panel, textStyle: { color: colors.fg } },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: colors.border, opacity: 0.55 } }, axisLabel: { color: colors.ghost } },
    yAxis: {
      type: 'category',
      data: stats.map(s => s.label),
      axisLabel: { color: colors.ghost },
      axisLine: { lineStyle: { color: colors.border } },
      axisTick: { show: false },
    },
    series: [{ type: 'bar', barMaxWidth: 20, data: stats.map(s => ({ value: s.value, itemStyle: { color: s.color } })) }],
  }), [colors, stats]);
  return <EChart option={option} className={className} />;
}
