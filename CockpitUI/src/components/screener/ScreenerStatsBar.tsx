'use client';

import { memo } from 'react';
import type { ScreenerBreadthStat } from '@/domain/screener';

interface ScreenerStatsBarProps {
  stats: ScreenerBreadthStat[];
  total: number;
}

function statColor(pct: number): string {
  if (pct >= 60) return '#0dbd7d';
  if (pct >= 40) return '#e8933a';
  return '#f23d55';
}

export const ScreenerStatsBar = memo(({ stats, total }: ScreenerStatsBarProps) => {
  return (
    <div className="shrink-0 border-b border-subtle bg-base/70 px-4 py-2">
      <div className="flex flex-wrap gap-2">
        <div className="min-w-28 rounded-md border border-border bg-card px-3 py-2">
          <div className="text-[10px] font-bold tracking-[0.1em] uppercase text-muted">Universe</div>
          <div className="mt-1 text-[17px] font-black tabular-nums text-fg">{total}</div>
        </div>
        {stats.map(stat => (
          <div key={stat.key} className="min-w-36 rounded-md border border-border bg-card px-3 py-2">
            <div className="text-[10px] font-bold tracking-[0.1em] uppercase text-muted">{stat.label}</div>
            <div className="mt-1 flex items-baseline justify-between gap-3">
              <span className="text-[17px] font-black tabular-nums text-fg">
                {stat.count}<span className="text-[12px] text-muted">/{stat.eligible}</span>
              </span>
              <span className="text-[13px] font-bold tabular-nums" style={{ color: statColor(stat.pct) }}>
                {stat.pct.toFixed(0)}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

ScreenerStatsBar.displayName = 'ScreenerStatsBar';