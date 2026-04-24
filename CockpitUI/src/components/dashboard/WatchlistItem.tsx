'use client';

import { memo } from 'react';
import type { ScoredSymbol } from '@/domain/dashboard';
import { LivePrice } from '@/components/ui/LivePrice';
import type { LivePriceData } from '@/components/ui/LivePrice';
import { cn } from '@/lib/cn';
import { comfortColor } from '@/lib/scoreColors';
import { stageColor, stageLabel } from '@/lib/stageUtils';

interface WatchlistItemProps {
  row: ScoredSymbol;
  selected: boolean;
  livePrice?: LivePriceData;
  marketOpen: boolean;
  onSelect: (sym: string) => void;
}

export const WatchlistItem = memo(({ row, selected: isSel, livePrice, marketOpen, onSelect }: WatchlistItemProps) => (
  <button type="button" onClick={() => onSelect(row.symbol)}
    className={cn(
      'flex w-full items-center gap-2 border-b border-border/40 border-l-2 px-3 py-2 text-left transition-colors hover:bg-lift/50',
      isSel ? 'bg-lift border-l-accent' : 'border-l-transparent',
    )}>
    <span className="num w-5 shrink-0 text-[10px] text-ghost">{row.rank}</span>
    <div className="min-w-0 flex-1">
      <div className="flex items-center gap-1">
        <span className={cn('text-[12px] font-black', isSel ? 'text-accent' : 'text-fg')}>
          {row.symbol}
        </span>
        {row.is_fno          && <span className="text-[8px] font-black text-violet">F&O</span>}
        {row.is_new_watchlist && <span className="text-[8px] font-black text-accent">NEW</span>}
        {row.nr7              && <span className="text-[8px] font-black text-sky">NR7</span>}
      </div>
      <div className="flex items-center gap-2 font-mono text-[9px] text-ghost">
        <LivePrice ltp={livePrice?.ltp ?? undefined} prevClose={livePrice?.prevClose ?? row.prev_day_close ?? undefined} marketOpen={marketOpen} />
        <span title="Total score (0–100)">T <span className="text-accent">{row.total_score.toFixed(0)}</span></span>
        {row.comfort_score != null && (
          <span title="Comfort score — hold-ease index (0–100)">
            C <span style={{ color: comfortColor(row.comfort_score) }}>{row.comfort_score.toFixed(0)}</span>
          </span>
        )}
        <span className="font-black" title="Weinstein stage" style={{ color: stageColor(row.stage) }}>
          {stageLabel(row.stage)}
        </span>
      </div>
    </div>
  </button>
));
WatchlistItem.displayName = 'WatchlistItem';
