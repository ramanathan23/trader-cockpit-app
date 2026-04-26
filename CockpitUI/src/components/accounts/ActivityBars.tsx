'use client';

import { useMemo } from 'react';
import { EChart } from '@/components/charts/EChart';
import { useEChartColors } from '@/components/charts/useEChartColors';
import type { Dashboard } from './accountTypes';
import { money } from './accountFmt';
import { activityBarsOption } from './activityBarsOption';

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

  const option = useMemo(() => activityBarsOption(rows, maxTrades, colors), [colors, maxTrades, rows]);

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
