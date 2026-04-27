'use client';

import { memo } from 'react';
import { fmt2, fmtAdv } from '@/lib/fmt';
import { screenerF52hColor, screenerPctText, screenerStageColor, screenerStageLabel } from '@/lib/screenerDisplay';
import type { StockRow } from '@/domain/stocklist';

interface ScorePanelProps { row: StockRow; }

export const StockListScorePanel = memo(({ row }: ScorePanelProps) => {
  const price = row.display_price ?? row.prev_day_close;
  return (
    <div className="flex h-full flex-col gap-2 rounded-lg border border-border/50 bg-card/70 p-3">
      <div className="label-sm">Overview</div>
      <div className="flex flex-col gap-1.5 text-[11px]">
        <div className="flex justify-between">
          <span className="text-ghost">Stage</span>
          <span className="font-black" style={{ color: screenerStageColor(row.stage) }}>{screenerStageLabel(row.stage)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-ghost">Price</span>
          <span className="num font-black text-fg">{price != null ? fmt2(price) : '—'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-ghost">ATR</span>
          <span className="num text-dim">{row.atr_14 != null ? fmt2(row.atr_14) : '—'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-ghost">ADV</span>
          <span className="num text-dim">{fmtAdv(row.adv_20_cr)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-ghost">52H%</span>
          <span className="num font-black" style={{ color: screenerF52hColor(row.f52h) }}>
            {row.f52h != null ? screenerPctText(row.f52h, true) : '—'}
          </span>
        </div>
      </div>
    </div>
  );
});
StockListScorePanel.displayName = 'StockListScorePanel';
