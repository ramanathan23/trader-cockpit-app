'use client';

import { memo, useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import { EChart } from '@/components/charts/EChart';
import { useEChartColors } from '@/components/charts/useEChartColors';
import type { TradeRow } from './accountTypes';
import { money } from './accountFmt';

const MAX_BARS = 180;

export const TradeBars = memo(function TradeBars({ trades }: { trades: TradeRow[] }) {
  const colors = useEChartColors();

  const sorted = useMemo(() => [...trades]
    .sort((a, b) => (a.exit_time ?? '').localeCompare(b.exit_time ?? ''))
    .slice(-MAX_BARS), [trades]);
  const wins = sorted.filter(t => t.pnl > 0).length;
  const losses = sorted.filter(t => t.pnl < 0).length;

  const option = useMemo<EChartsOption>(() => ({
    backgroundColor: 'transparent',
    grid: { left: 8, right: 8, top: 10, bottom: 24 },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      borderColor: colors.border,
      backgroundColor: colors.panel,
      textStyle: { color: colors.fg, fontFamily: 'JetBrains Mono, Fira Code, monospace', fontSize: 11 },
      formatter: params => {
        const item = Array.isArray(params) ? params[0] : params;
        const trade = sorted[(item as { dataIndex?: number } | undefined)?.dataIndex ?? 0];
        if (!trade) return '';
        return `<b>${trade.symbol}</b><br/>${trade.exit_time?.slice(0, 10) ?? '-'}<br/>P&L: ${money(trade.pnl)}`;
      },
    },
    xAxis: {
      type: 'category',
      data: sorted.map((trade, idx) => trade.exit_time?.slice(5, 10) ?? `${idx + 1}`),
      axisLine: { lineStyle: { color: colors.border } },
      axisTick: { show: false },
      axisLabel: { color: colors.ghost, fontSize: 8, showMinLabel: true, showMaxLabel: true, hideOverlap: true },
    },
    yAxis: {
      type: 'value',
      splitLine: { show: false },
      axisLabel: { show: false },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [{
      type: 'bar',
      data: sorted.map(trade => ({
        value: trade.pnl,
        itemStyle: { color: trade.pnl >= 0 ? colors.bull : colors.bear, opacity: 0.78 },
      })),
      barMaxWidth: 18,
      markLine: {
        symbol: 'none',
        silent: true,
        lineStyle: { color: colors.border },
        label: { show: false },
        data: [{ yAxis: 0 }],
      },
    }],
  }), [colors, sorted]);

  if (!trades.length) {
    return (
      <div className="flex h-28 items-center justify-center rounded-lg border border-dashed border-border bg-panel">
        <span className="text-[11px] text-ghost">Trade P&L bars - awaiting first trade sync</span>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-panel p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-[13px] font-black text-fg">Trade-by-Trade P&L</span>
        <span className="text-[11px] text-ghost">
          <span className="font-black text-bull">{wins}W</span>
          <span className="mx-1 text-ghost">/</span>
          <span className="font-black text-bear">{losses}L</span>
          <span className="ml-2">{sorted.length}/{trades.length} shown</span>
        </span>
      </div>
      <EChart option={option} className="h-28 w-full" />
    </div>
  );
});
TradeBars.displayName = 'TradeBars';
