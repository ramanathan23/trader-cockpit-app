'use client';

import { memo } from 'react';
import { ScoreBar } from '@/components/dashboard/ScoreBar';
import type { StockRow } from '@/domain/stocklist';

interface ScorePanelProps { row: StockRow; }

export const StockListScorePanel = memo(({ row }: ScorePanelProps) => {
  if (row.total_score == null) {
    return <div className="text-[11px] text-ghost">Not scored — run pipeline.</div>;
  }
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border/50 bg-card/60 p-3">
      <div className="label-sm mb-0.5">Score Breakdown</div>
      <ScoreBar value={row.momentum_score  ?? 0} color="accent" label="MOM" />
      <ScoreBar value={row.trend_score     ?? 0} color="bull"   label="TRD" />
      <ScoreBar value={row.volatility_score ?? 0} color="amber" label="VOL" />
      <ScoreBar value={row.structure_score ?? 0} color="sky"    label="STR" />
      {row.comfort_score != null && (
        <ScoreBar value={row.comfort_score} color="violet" label="CMF" />
      )}
      <div className="mt-1.5 flex items-baseline justify-end gap-1 border-t border-border/50 pt-2">
        <span className="num text-[26px] font-black text-fg">{row.total_score.toFixed(0)}</span>
        <span className="text-[11px] text-ghost">/ 100</span>
      </div>
    </div>
  );
});
StockListScorePanel.displayName = 'StockListScorePanel';
