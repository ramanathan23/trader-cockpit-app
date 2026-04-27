'use client';

import { memo } from 'react';
import { ScoreBar } from '@/components/dashboard/ScoreBar';
import type { StockRow } from '@/domain/stocklist';

interface ScorePanelProps { row: StockRow; }

function scoreTone(value: number) {
  if (value >= 80) return 'text-bull';
  if (value >= 65) return 'text-accent';
  if (value >= 50) return 'text-amber';
  return 'text-bear';
}

export const StockListScorePanel = memo(({ row }: ScorePanelProps) => {
  if (row.total_score == null) {
    return (
      <div className="rounded-lg border border-border/50 bg-card/70 p-3 text-[11px] text-ghost">
        Not scored - run pipeline.
      </div>
    );
  }

  const total = row.total_score;

  return (
    <div className="flex h-full flex-col rounded-lg border border-border/50 bg-card/70 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="label-sm">Score</div>
          <div className="mt-1 text-[11px] text-ghost">Momentum setup quality</div>
        </div>
        <div className="text-right">
          <span className={`num text-[30px] font-black leading-none ${scoreTone(total)}`}>{total.toFixed(0)}</span>
          <span className="ml-1 text-[11px] text-ghost">/100</span>
        </div>
      </div>

      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-border/50">
        <div
          className="h-full rounded-full bg-accent"
          style={{ width: `${Math.min(100, Math.max(0, total))}%` }}
        />
      </div>

      <div className="mt-4 flex flex-col gap-2">
        <ScoreBar value={row.momentum_score ?? 0} color="accent" label="MOM" />
        <ScoreBar value={row.trend_score ?? 0} color="bull" label="TRD" />
        <ScoreBar value={row.volatility_score ?? 0} color="amber" label="VOL" />
        <ScoreBar value={row.structure_score ?? 0} color="sky" label="STR" />
      </div>
    </div>
  );
});
StockListScorePanel.displayName = 'StockListScorePanel';
