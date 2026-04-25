'use client';

import { useEffect, useMemo, useRef } from 'react';
import {
  createChart, LineSeries,
  type IChartApi, type ISeriesApi, type LineData, type Time,
} from 'lightweight-charts';
import type { Dashboard } from './accountTypes';
import { money } from './accountFmt';

const PCT_RANGE = { priceRange: { minValue: 0, maxValue: 100 } };

export function ActivityBars({ daily }: { daily: Dashboard['daily'] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<{
    trades: ISeriesApi<'Line'> | null;
    wins: ISeriesApi<'Line'> | null;
    losses: ISeriesApi<'Line'> | null;
  }>({ trades: null, wins: null, losses: null });

  const rows = useMemo(() => daily.slice(-28), [daily]);
  const totals = useMemo(() => {
    const trades = rows.reduce((sum, row) => sum + (row.trades ?? 0), 0);
    const wins = rows.reduce((sum, row) => sum + (row.wins ?? 0), 0);
    const losses = rows.reduce((sum, row) => sum + (row.losses ?? 0), 0);
    const executions = rows.reduce((sum, row) => sum + row.executions, 0);
    return { trades, wins, losses, executions, winRate: trades ? Math.round((wins / trades) * 100) : 0 };
  }, [rows]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      height: 128,
      layout: { background: { color: 'transparent' }, textColor: 'rgb(var(--ghost))', fontSize: 10 },
      grid: { vertLines: { color: 'rgba(109,124,132,0.14)' }, horzLines: { color: 'rgba(109,124,132,0.14)' } },
      crosshair: { vertLine: { color: 'rgba(34,153,139,0.3)', width: 1, style: 2 }, horzLine: { color: 'rgba(34,153,139,0.3)', width: 1, style: 2 } },
      timeScale: { borderColor: 'rgba(109,124,132,0.35)', timeVisible: false },
      rightPriceScale: { borderColor: 'rgba(109,124,132,0.35)' },
    });
    chartRef.current = chart;

    const fixedPercentScale = () => PCT_RANGE;
    const trades = chart.addSeries(LineSeries, {
      color: 'rgb(var(--accent))', lineWidth: 2, priceLineVisible: false,
      title: 'Trades % of peak', autoscaleInfoProvider: fixedPercentScale,
    });
    const wins = chart.addSeries(LineSeries, {
      color: 'rgb(var(--bull))', lineWidth: 2, priceLineVisible: false,
      title: 'Win %', autoscaleInfoProvider: fixedPercentScale,
    });
    const losses = chart.addSeries(LineSeries, {
      color: 'rgb(var(--bear))', lineWidth: 2, priceLineVisible: false,
      title: 'Loss %', autoscaleInfoProvider: fixedPercentScale,
    });
    seriesRef.current = { trades, wins, losses };

    const ro = new ResizeObserver(entries => {
      chart.applyOptions({ width: entries[0].contentRect.width, height: 128 });
    });
    ro.observe(container);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = { trades: null, wins: null, losses: null };
    };
  }, []);

  useEffect(() => {
    const maxTrades = Math.max(1, ...rows.map(row => row.trades ?? 0));
    const tradeData: LineData<Time>[] = rows.map(row => ({
      time: row.date as Time,
      value: Math.round(((row.trades ?? 0) / maxTrades) * 100),
    }));
    const winData: LineData<Time>[] = rows.map(row => ({ time: row.date as Time, value: row.win_pct ?? 0 }));
    const lossData: LineData<Time>[] = rows.map(row => ({ time: row.date as Time, value: row.loss_pct ?? 0 }));
    seriesRef.current.trades?.setData(tradeData);
    seriesRef.current.wins?.setData(winData);
    seriesRef.current.losses?.setData(lossData);
    chartRef.current?.timeScale().fitContent();
  }, [rows]);

  return (
    <div className="h-52 rounded-lg border border-border bg-panel p-3">
      <div className="mb-2 flex items-start justify-between gap-3">
        <div>
          <span className="block text-[12px] font-black text-fg">Trades vs Win/Loss Since Apr 2026</span>
          <div className="mt-1 flex flex-wrap gap-2 text-[10px] text-ghost">
            <Legend color="bg-accent" label="Trades % of peak" />
            <Legend color="bg-bull" label="Win %" />
            <Legend color="bg-bear" label="Loss %" />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2 text-right">
          <Metric value={money(totals.trades)} label="trades" />
          <Metric value={`${totals.winRate}%`} label="win rate" tone="text-bull" />
          <Metric value={money(totals.executions)} label="fills" />
        </div>
      </div>
      <div className="relative h-32 w-full">
        <div ref={containerRef} className="h-full w-full" />
        {!rows.length && (
        <div className="absolute inset-0 flex items-center justify-center rounded border border-dashed border-border bg-panel text-[11px] text-ghost">
          No closed trades synced yet.
        </div>
        )}
      </div>
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
