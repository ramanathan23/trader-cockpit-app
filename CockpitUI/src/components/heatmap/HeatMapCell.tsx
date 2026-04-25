'use client';

import { memo } from 'react';
import { heatChgColor, heatSize, heatTextColor, heatTone } from '@/lib/heatmap';
import type { HeatMapEntry } from '@/lib/heatmap';
import { fmt2 } from '@/lib/fmt';

interface HeatMapCellProps {
  entry:   HeatMapEntry;
  onClick: (symbol: string) => void;
}

export const HeatMapCell = memo(({ entry, onClick }: HeatMapCellProps) => {
  const { symbol, adv, chgPct, price, score, stage, signal } = entry;
  const size = heatSize(adv, chgPct);
  const tone = heatTone(chgPct);

  return (
    <button
      role="button"
      onClick={() => onClick(symbol)}
      title={`${symbol}${chgPct != null ? ` ${chgPct.toFixed(2)}%` : ''}`}
      className="group relative flex shrink-0 cursor-pointer flex-col justify-between overflow-hidden rounded-lg border border-white/10 p-2 text-left shadow-sm outline-none transition hover:-translate-y-0.5 hover:border-white/30 focus-visible:ring-2 focus-visible:ring-accent/60"
      style={{
        width:      size.w,
        height:     size.h,
        flexShrink: 0,
        background: heatChgColor(chgPct),
        color:      heatTextColor(chgPct),
      }}
    >
      <span
        className="pointer-events-none absolute inset-x-0 top-0 h-1 opacity-80"
        style={{
          background: tone === 'bull' ? '#baf7d8' : tone === 'bear' ? '#ffd0d6' : 'rgb(var(--rim))',
        }}
      />
      <span className="min-w-0">
        <span className="block truncate text-[11px] font-black leading-none">{symbol}</span>
        {signal && <span className="mt-1 block truncate text-[8px] font-black uppercase opacity-75">{signal}</span>}
      </span>
      <span className="space-y-1">
        {price != null && <span className="num block truncate text-[10px] font-black leading-none">{fmt2(price)}</span>}
        <span className="flex items-end justify-between gap-1">
          <span className="num text-[11px] font-black leading-none">
            {chgPct != null ? `${chgPct > 0 ? '+' : ''}${chgPct.toFixed(2)}%` : '-'}
          </span>
          {score != null && <span className="num rounded bg-black/18 px-1 text-[9px] font-black leading-4">{score.toFixed(0)}</span>}
        </span>
        {stage && <span className="block truncate text-[8px] font-black uppercase opacity-70">{stage}</span>}
      </span>
    </button>
  );
});
HeatMapCell.displayName = 'HeatMapCell';
