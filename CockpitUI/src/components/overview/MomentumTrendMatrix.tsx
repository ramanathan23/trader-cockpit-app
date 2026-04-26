'use client';

import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import type { StockRow } from '@/domain/stocklist';
import { EChart } from '@/components/charts/EChart';
import { useEChartColors } from '@/components/charts/useEChartColors';
import { fmt2 } from '@/lib/fmt';
import type { RowsProps, SymbolClickProps } from './overviewTypes';

export function MomentumTrendMatrix({ rows, onSymbol }: RowsProps & SymbolClickProps) {
  const colors = useEChartColors();
  const dataRows = useMemo(
    () => rows.filter(row => row.momentum_score != null && row.trend_score != null).slice(0, 180),
    [rows],
  );
  const option = useMemo<EChartsOption>(() => ({
    backgroundColor: 'transparent',
    grid: { left: 38, right: 12, top: 18, bottom: 34 },
    tooltip: {
      trigger: 'item',
      borderColor: colors.border,
      backgroundColor: colors.panel,
      textStyle: { color: colors.fg, fontFamily: 'JetBrains Mono, Fira Code, monospace', fontSize: 11 },
      formatter: params => {
        const row = (params as { data?: { row?: StockRow } }).data?.row;
        if (!row) return '';
        return `<b>${row.symbol}</b><br/>Momentum: ${fmt2(row.momentum_score)}<br/>Trend: ${fmt2(row.trend_score)}<br/>Score: ${fmt2(row.total_score)}`;
      },
    },
    xAxis: axis('Momentum', colors),
    yAxis: axis('Trend', colors),
    series: [{
      type: 'scatter',
      data: dataRows.map(row => ({
        name: row.symbol,
        row,
        value: [row.momentum_score, row.trend_score],
        symbolSize: Math.max(7, Math.min(18, (row.total_score ?? 50) / 5)),
        itemStyle: { color: dotColor(row, colors), opacity: 0.68 },
      })),
      markLine: { symbol: 'none', silent: true, lineStyle: { color: colors.accent, type: 'dashed', opacity: 0.25 }, label: { show: false }, data: [{ xAxis: 65 }, { yAxis: 65 }] },
    }],
  }), [colors, dataRows]);
  return (
    <EChart option={option} className="h-64 w-full" onClick={params => {
      const row = (params as { data?: { row?: StockRow } }).data?.row;
      if (row?.symbol) onSymbol(row.symbol);
    }} />
  );
}

function axis(name: string, colors: ReturnType<typeof useEChartColors>) {
  return {
    name, min: 0, max: 100,
    splitLine: { lineStyle: { color: colors.border, opacity: 0.55 } },
    axisLabel: { color: colors.ghost },
    axisLine: { lineStyle: { color: colors.border } },
    nameTextStyle: { color: colors.dim },
  };
}

function dotColor(row: StockRow, colors: ReturnType<typeof useEChartColors>) {
  if (row.weekly_bias === 'BEARISH') return colors.bear;
  if (row.weekly_bias === 'BULLISH') return colors.bull;
  return colors.amber;
}
