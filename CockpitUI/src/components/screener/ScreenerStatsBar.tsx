'use client';

import { memo } from 'react';
import type { ScreenerBreadthStat } from '@/domain/screener';

interface ScreenerStatsBarProps {
  stats: ScreenerBreadthStat[];
  total: number;
}

function statColor(pct: number): string {
  if (pct >= 60) return 'rgb(var(--bull))';
  if (pct >= 40) return 'rgb(var(--amber))';
  return 'rgb(var(--bear))';
}

export const ScreenerStatsBar = memo(({ stats, total }: ScreenerStatsBarProps) => (
  <div className="shrink-0 border-b border-border bg-base/45 px-4 py-3">
    <div className="flex gap-2 overflow-x-auto">
      <div className="metric-card">
        <div className="text-[10px] font-black uppercase text-ghost">Universe</div>
        <div className="num mt-1 text-[19px] font-black text-fg">{total}</div>
      </div>
      {stats.map(stat => (
        <div key={stat.key} className="metric-card">
          <div className="text-[10px] font-black uppercase text-ghost">{stat.label}</div>
          <div className="mt-1 flex items-baseline justify-between gap-4">
            <span className="num text-[19px] font-black text-fg">
              {stat.count}<span className="text-[12px] text-ghost">/{stat.eligible}</span>
            </span>
            <span className="num text-[14px] font-black" style={{ color: statColor(stat.pct) }}>
              {stat.pct.toFixed(0)}%
            </span>
          </div>
        </div>
      ))}
    </div>
  </div>
));

ScreenerStatsBar.displayName = 'ScreenerStatsBar';
