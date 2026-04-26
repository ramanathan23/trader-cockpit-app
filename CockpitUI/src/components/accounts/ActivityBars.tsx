'use client';

import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import { EChart } from '@/components/charts/EChart';
import { useEChartColors } from '@/components/charts/useEChartColors';
import type { Dashboard } from './accountTypes';
import { money } from './accountFmt';

export function ActivityBars({ daily }: { daily: Dashboard['daily'] }) {
  const colors = useEChartColors();
  const rows = daily.slice(-28);
  const totals = rows.reduce(
    (acc, row) => {
      acc.trades += row.trades ?? 0;
      acc.wins += row.wins ?? 0;
      acc.losses += row.losses ?? 0;
      acc.executions += row.executions;
      return acc;
    },
    { trades: 0, wins: 0, losses: 0, executions: 0 },
  );
  const winRate = totals.trades ? Math.round((totals.wins / totals.trades) * 100) : 0;
  const maxTrades = Math.max(1, ...rows.map(row => row.trades ?? 0));

  const option = useMemo<EChartsOption>(() => ({
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
      {
        name: 'Trades',
        type: 'line',
        smooth: true,
        symbolSize: 4,
        lineStyle: { width: 2.2 },
        data: rows.map(row => ((row.trades ?? 0) / maxTrades) * 100),
      },
      {
        name: 'Win %',
        type: 'line',
        smooth: true,
        symbolSize: 4,
        lineStyle: { width: 2.2 },
        data: rows.map(row => row.win_pct ?? 0),
      },
      {
        name: 'Loss %',
        type: 'line',
        smooth: true,
        symbolSize: 4,
        lineStyle: { width: 2.2 },
        data: rows.map(row => row.loss_pct ?? 0),
      },
    ],
  }), [colors, maxTrades, rows]);

  return (
    <div className="rounded-lg border border-border bg-panel p-3">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <span className="block text-[12px] font-black text-fg">Trades vs Win/Loss Since Apr 2026</span>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-ghost">
            <Legend color="bg-accent" label={`Trades, scaled to peak ${money(maxTrades)}`} />
            <Legend color="bg-bull" label="Win %" />
            <Legend color="bg-bear" label="Loss %" />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3 text-right">
          <Metric value={money(totals.trades)} label="trades" />
          <Metric value={`${winRate}%`} label="win rate" tone="text-bull" />
          <Metric value={money(totals.executions)} label="fills" />
        </div>
      </div>

      {rows.length ? (
        <EChart option={option} className="h-40 w-full" />
      ) : (
        <div className="flex h-40 items-center justify-center rounded border border-dashed border-border text-[11px] text-ghost">
          No closed trades synced yet.
        </div>
      )}

      <div className="mt-1 flex justify-end gap-3 text-[10px]">
        <span className="num text-bull">{totals.wins} wins</span>
        <span className="num text-bear">{totals.losses} losses</span>
      </div>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return <span className="inline-flex items-center gap-1"><span className={`h-1.5 w-3 rounded-full ${color}`} />{label}</span>;
}

function Metric({ value, label, tone = 'text-fg' }: { value: string; label: string; tone?: string }) {
  return (
    <span>
      <span className={`num block text-[13px] font-black ${tone}`}>{value}</span>
      <span className="block text-[10px] text-ghost">{label}</span>
    </span>
  );
}
