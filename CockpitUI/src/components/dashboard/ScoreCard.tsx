'use client';

import { LivePrice } from '@/components/ui/LivePrice';
import type { LivePriceData } from '@/components/ui/LivePrice';
import { Badge } from '@/components/ui/Badge';
import { fmt2, fmtAdv } from '@/lib/fmt';
import { comfortColor, rsiColor } from '@/lib/scoreColors';
import type { ScoredSymbol } from '@/domain/dashboard';
import { ScoreBar } from './ScoreBar';
import { StageBadge } from './StageBadge';
import type { SymbolModalTab } from './SymbolModal';

interface ScoreCardProps {
  row: ScoredSymbol;
  livePrice?: LivePriceData;
  marketOpen: boolean;
  onOpen: (sym: string, tab?: SymbolModalTab) => void;
}

/** Card view tile for a single scored symbol — used in the grid layout. */
export function ScoreCard({ row, livePrice, marketOpen, onOpen }: ScoreCardProps) {
  return (
    <div className="rounded-lg border border-border bg-panel p-3 cursor-pointer transition-colors hover:border-accent/40 hover:bg-lift/60"
      onClick={() => onOpen(row.symbol, 'chart')}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-1">
            <span className="text-ticker text-fg">{row.symbol}</span>
            {row.is_fno           && <Badge size="sm" color="violet">F&O</Badge>}
            {row.is_watchlist     && <Badge size="sm" color="amber">WL</Badge>}
            {row.is_new_watchlist && <Badge size="sm" color="accent" title="New to watchlist in the last 7 days">NEW</Badge>}
            {row.bb_squeeze       && <Badge size="sm" color="violet">SQ{row.squeeze_days}</Badge>}
            {row.nr7              && <Badge size="sm" color="sky">NR7</Badge>}
          </div>
          <div className="mt-0.5 flex items-center gap-2">
            <LivePrice ltp={livePrice?.ltp ?? undefined} prevClose={livePrice?.prevClose ?? row.prev_day_close ?? undefined} marketOpen={marketOpen} />
            {row.company_name && <span className="max-w-full truncate text-[10px] text-ghost">{row.company_name}</span>}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="num text-[10px] text-ghost">#{row.rank}</span>
          <button type="button" onClick={e => { e.stopPropagation(); onOpen(row.symbol, 'oc'); }}
            className="text-[10px] font-black text-accent opacity-60 hover:opacity-100" title="View option chain">OC</button>
        </div>
      </div>

      <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1">
        <ScoreBar value={row.total_score}      color="accent"  label="Total" />
        <ScoreBar value={row.momentum_score}   color="amber"   label="Mom"   />
        <ScoreBar value={row.trend_score}      color="bull"    label="Trend" />
        <ScoreBar value={row.volatility_score} color="violet"  label="Vol"   />
      </div>

      <div className="mt-2 flex items-center justify-between text-[11px]">
        <span className="num text-ghost" title="ADX(14)">ADX <span className="text-fg">{row.adx_14 != null ? row.adx_14.toFixed(0) : '-'}</span></span>
        <span className="num text-ghost" title="RSI(14)">RSI <span style={{ color: rsiColor(row.rsi_14) }}>{row.rsi_14 != null ? row.rsi_14.toFixed(0) : '-'}</span></span>
        <span className="num text-ghost" title="Average daily value (20-day)">ADV <span className="text-fg">{fmtAdv(row.adv_20_cr)}</span></span>
        {row.comfort_score != null && (
          <span className="num text-ghost" title={row.comfort_interpretation ?? 'Comfort score'}>
            C <span style={{ color: comfortColor(row.comfort_score) }}>{row.comfort_score.toFixed(0)}</span>
          </span>
        )}
        <StageBadge stage={row.stage} />
      </div>
    </div>
  );
}
