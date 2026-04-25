'use client';

import { memo } from 'react';
import { heatChgColor, heatTextColor, heatWidth } from '@/lib/heatmap';
import type { HeatMapEntry } from '@/lib/heatmap';

interface HeatMapCellProps {
  entry:   HeatMapEntry;
  onClick: (symbol: string) => void;
}

export const HeatMapCell = memo(({ entry, onClick }: HeatMapCellProps) => {
  const { symbol, adv, chgPct, score } = entry;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onClick(symbol)}
      onKeyDown={e => e.key === 'Enter' && onClick(symbol)}
      className="flex cursor-pointer flex-col items-center justify-center gap-0.5 overflow-hidden rounded p-1 transition-opacity hover:opacity-80"
      style={{
        width:      heatWidth(adv),
        height:     56,
        flexShrink: 0,
        background: heatChgColor(chgPct),
        color:      heatTextColor(chgPct),
      }}
    >
      <span className="text-[11px] font-black leading-none tracking-tight">{symbol}</span>
      {chgPct != null && (
        <span className="num text-[10px] leading-none">
          {chgPct > 0 ? '+' : ''}{chgPct.toFixed(2)}%
        </span>
      )}
      {score != null && (
        <span className="num text-[9px] leading-none opacity-70">{score.toFixed(0)}</span>
      )}
    </div>
  );
});
HeatMapCell.displayName = 'HeatMapCell';
