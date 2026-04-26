'use client';

import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import { EChart } from '@/components/charts/EChart';
import { useEChartColors } from '@/components/charts/useEChartColors';
import type { RowsProps } from './overviewTypes';

const BUCKETS = [
  { label: '<40', min: -Infinity, max: 40 },
  { label: '40-50', min: 40, max: 50 },
  { label: '50-60', min: 50, max: 60 },
  { label: '60-70', min: 60, max: 70 },
  { label: '70-80', min: 70, max: 80 },
  { label: '80+', min: 80, max: Infinity },
];

export function ScoreHistogram({ rows }: RowsProps) {
  const colors = useEChartColors();
  const option = useMemo<EChartsOption>(() => ({
    backgroundColor: 'transparent',
    grid: { left: 34, right: 12, top: 18, bottom: 28 },
    tooltip: { trigger: 'axis', borderColor: colors.border, backgroundColor: colors.panel, textStyle: { color: colors.fg } },
    xAxis: {
      type: 'category',
      data: BUCKETS.map(b => b.label),
      axisLabel: { color: colors.ghost },
      axisLine: { lineStyle: { color: colors.border } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: colors.border, opacity: 0.55 } },
      axisLabel: { color: colors.ghost },
    },
    series: [{
      type: 'bar',
      barMaxWidth: 34,
      data: BUCKETS.map(bucket => {
        const value = rows.filter(row => {
          const score = row.total_score ?? 0;
          return score >= bucket.min && score < bucket.max;
        }).length;
        return { value, itemStyle: { color: bucketColor(bucket.min, colors) } };
      }),
    }],
  }), [colors, rows]);

  return <EChart option={option} className="h-64 w-full" />;
}

function bucketColor(min: number, colors: ReturnType<typeof useEChartColors>) {
  if (min >= 70) return colors.bull;
  if (min >= 60) return colors.accent;
  if (min >= 50) return colors.amber;
  return colors.rim;
}

