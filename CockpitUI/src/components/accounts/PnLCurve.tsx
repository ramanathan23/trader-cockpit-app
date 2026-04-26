'use client';

import { memo, useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import { EChart } from '@/components/charts/EChart';
import { useEChartColors } from '@/components/charts/useEChartColors';
import type { TradeRow } from './accountTypes';
import { money } from './accountFmt';

export const PnLCurve = memo(function PnLCurve({ trades }: { trades: TradeRow[] }) {
  const colors = useEChartColors();
  const sorted = useMemo(() => [...trades].sort((a, b) => (a.exit_time ?? '').localeCompare(b.exit_time ?? '')), [trades]);
  const points = useMemo(() => {
    let running = 0;
    return sorted.map(trade => {
      running += trade.pnl;
      return { trade, running };
    });
  }, [sorted]);
  const total = points[points.length - 1]?.running ?? 0;
  const isPos = total >= 0;

  const option = useMemo<EChartsOption>(() => ({
    backgroundColor: 'transparent',
    grid: { left: 54, right: 14, top: 12, bottom: 26 },
    tooltip: {
      trigger: 'axis',
      borderColor: colors.border,
      backgroundColor: colors.panel,
      textStyle: { color: colors.fg, fontFamily: 'JetBrains Mono, Fira Code, monospace', fontSize: 11 },
      formatter: params => {
        const item = Array.isArray(params) ? params[0] : params;
        const point = points[(item as { dataIndex?: number } | undefined)?.dataIndex ?? 0];
        if (!point) return '';
        const day = point.trade.exit_time?.slice(0, 10) ?? '-';
        return `<b>${point.trade.symbol}</b><br/>${day}<br/>Trade: ${money(point.trade.pnl)}<br/>Cumulative: ${money(point.running)}`;
      },
    },
    xAxis: {
      type: 'category',
      data: points.map((point, idx) => point.trade.exit_time?.slice(5, 10) ?? `${idx + 1}`),
      axisLine: { lineStyle: { color: colors.border } },
      axisTick: { show: false },
      axisLabel: { color: colors.ghost, fontFamily: 'JetBrains Mono, Fira Code, monospace', fontSize: 9, hideOverlap: true },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: colors.border, opacity: 0.6 } },
      axisLabel: {
        color: colors.ghost,
        fontFamily: 'JetBrains Mono, Fira Code, monospace',
        fontSize: 9,
        formatter: (value: number) => Math.abs(value) >= 1000 ? `${Math.round(value / 1000)}k` : `${Math.round(value)}`,
      },
    },
    series: [{
      type: 'line',
      smooth: true,
      symbol: points.length <= 20 ? 'circle' : 'none',
      symbolSize: 5,
      data: points.map(point => point.running),
      lineStyle: { width: 2.2, color: isPos ? colors.bull : colors.bear },
      itemStyle: { color: isPos ? colors.bull : colors.bear },
      areaStyle: { color: isPos ? `${colors.bull}22` : `${colors.bear}22` },
      markLine: {
        symbol: 'none',
        silent: true,
        lineStyle: { color: colors.border, type: 'dashed' },
        label: { show: false },
        data: [{ yAxis: 0 }],
      },
    }],
  }), [colors, isPos, points]);

  if (!points.length) {
    return (
      <div className="flex h-44 flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-border bg-panel">
        <div className="text-[22px] font-black text-ghost/25">P&L</div>
        <div className="text-[11px] text-ghost">Cumulative curve - awaiting first trade sync</div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-panel p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-[13px] font-black text-fg">Cumulative P&L</span>
        <span className={`num text-[13px] font-black ${isPos ? 'text-bull' : 'text-bear'}`}>{money(total)}</span>
      </div>
      <EChart option={option} className="h-40 w-full" />
    </div>
  );
});
PnLCurve.displayName = 'PnLCurve';
