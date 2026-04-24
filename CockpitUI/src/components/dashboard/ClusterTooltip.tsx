'use client';

import { memo } from 'react';
import type { ScoredSymbol } from '@/domain/dashboard';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/cn';
import { comfortColor } from '@/lib/scoreColors';

interface ClusterTooltipProps {
  hoveredRow:   ScoredSymbol | null;
  mousePos:     { x: number; y: number };
  containerRef: React.RefObject<HTMLDivElement | null>;
}

const TT_W = 220;
const TT_H = 140;

export const ClusterTooltip = memo(({ hoveredRow, mousePos, containerRef }: ClusterTooltipProps) => {
  if (!hoveredRow) return null;
  const cW   = containerRef.current?.offsetWidth  ?? 900;
  const cH   = containerRef.current?.offsetHeight ?? 540;
  const left = Math.min(Math.max(4, mousePos.x + 18), cW - TT_W - 8);
  const top  = Math.min(Math.max(4, mousePos.y - TT_H / 2), cH - TT_H - 32);

  const biasCls = hoveredRow.weekly_bias === 'BULLISH' ? 'text-bull'
    : hoveredRow.weekly_bias === 'BEARISH' ? 'text-bear' : 'text-ghost';

  return (
    <div className="pointer-events-none absolute z-20 rounded-md border border-border bg-panel shadow-lg"
      style={{ left, top, width: TT_W, backdropFilter: 'blur(6px)' }}>
      <div className="border-b border-border/50 px-3 py-2">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[13px] font-black text-fg">{hoveredRow.symbol}</span>
          {hoveredRow.is_fno           && <Badge size="sm" color="violet">F&O</Badge>}
          {hoveredRow.is_watchlist     && <Badge size="sm" color="amber">WL</Badge>}
          {hoveredRow.is_new_watchlist && <Badge size="sm" color="accent">NEW</Badge>}
          <span className="ml-auto font-mono text-[10px] text-ghost">#{hoveredRow.rank}</span>
        </div>
        {hoveredRow.company_name && <div className="mt-0.5 truncate font-mono text-[9px] text-ghost">{hoveredRow.company_name}</div>}
      </div>
      <div className="grid grid-cols-3 gap-x-2 gap-y-1 px-3 py-2 font-mono text-[10px]">
        <span className="text-ghost">Total   <span className="text-accent">{hoveredRow.total_score.toFixed(0)}</span></span>
        <span className="text-ghost">Mom     <span className="text-amber">{hoveredRow.momentum_score.toFixed(0)}</span></span>
        <span className="text-ghost">Trend   <span className="text-bull">{hoveredRow.trend_score?.toFixed(0) ?? '-'}</span></span>
        <span className="text-ghost">Comfort <span style={{ color: comfortColor(hoveredRow.comfort_score) }}>{hoveredRow.comfort_score?.toFixed(0) ?? '-'}</span></span>
        <span className="text-ghost">RSI     <span className="text-fg">{hoveredRow.rsi_14?.toFixed(0) ?? '-'}</span></span>
        <span className="text-ghost">ADX     <span className="text-fg">{hoveredRow.adx_14?.toFixed(0) ?? '-'}</span></span>
      </div>
      <div className="border-t border-border/50 px-3 py-1.5 font-mono text-[10px]">
        <span className="text-ghost">Bias </span>
        <span className={cn(biasCls)}>{hoveredRow.weekly_bias ?? 'NEUTRAL'}</span>
        {hoveredRow.comfort_interpretation && <span className="ml-3 italic text-ghost">{hoveredRow.comfort_interpretation}</span>}
      </div>
    </div>
  );
});
ClusterTooltip.displayName = 'ClusterTooltip';
