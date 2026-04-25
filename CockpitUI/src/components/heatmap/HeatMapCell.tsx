'use client';

import { memo } from 'react';
import { heatChgColor, heatSize, heatTextColor } from '@/lib/heatmap';
import type { HeatMapEntry } from '@/lib/heatmap';
import { fmt2 } from '@/lib/fmt';

interface HeatMapCellProps {
  entry:   HeatMapEntry;
  onClick: (symbol: string) => void;
  width?:  number | string;
  height?: number | string;
}

export const HeatMapCell = memo(({ entry, onClick, width, height }: HeatMapCellProps) => {
  const { symbol, adv, chgPct, price, score, stage, signal } = entry;
  const size = heatSize(adv, chgPct);
  const resolvedWidth = width ?? size.w;
  const resolvedHeight = height ?? size.h;
  const showMeta = typeof resolvedHeight === 'number' ? resolvedHeight >= 58 : true;
  const showStage = typeof resolvedHeight === 'number' ? resolvedHeight >= 76 : true;

  return (
    <button
      role="button"
      onClick={() => onClick(symbol)}
      title={`${symbol}${chgPct != null ? ` ${chgPct.toFixed(2)}%` : ''}`}
      className="group relative flex shrink-0 cursor-pointer flex-col justify-between overflow-hidden rounded border border-black/15 p-2 text-left outline-none transition-colors hover:border-white/40 focus-visible:ring-2 focus-visible:ring-accent/60"
      style={{
        width:      resolvedWidth,
        height:     resolvedHeight,
        flexShrink: 0,
        background: heatChgColor(chgPct),
        color:      heatTextColor(chgPct),
      }}
    >
      <span className="min-w-0">
        <span className="block truncate text-[11px] font-black leading-none">{symbol}</span>
        {showMeta && signal && <span className="mt-1 block truncate text-[8px] font-black uppercase opacity-75">{signal}</span>}
      </span>
      <span className="space-y-1">
        {showMeta && price != null && <span className="num block truncate text-[10px] font-black leading-none">{fmt2(price)}</span>}
        <span className="flex items-end justify-between gap-1">
          <span className="num text-[11px] font-black leading-none">
            {chgPct != null ? `${chgPct > 0 ? '+' : ''}${chgPct.toFixed(2)}%` : '-'}
          </span>
          {showMeta && score != null && <span className="num px-1 text-[9px] font-black leading-4">{score.toFixed(0)}</span>}
        </span>
        {showStage && stage && <span className="block truncate text-[8px] font-black uppercase opacity-70">{stage}</span>}
      </span>
    </button>
  );
});
HeatMapCell.displayName = 'HeatMapCell';
