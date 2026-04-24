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

interface ScoreRowProps {
  row: ScoredSymbol;
  livePrice?: LivePriceData;
  marketOpen: boolean;
  onOpen: (sym: string, tab?: SymbolModalTab) => void;
}

/** Table row for a single scored symbol — used in the virtualized table view. */
export function ScoreRow({ row, livePrice, marketOpen, onOpen }: ScoreRowProps) {
  return (
    <tr className="group cursor-pointer" onClick={() => onOpen(row.symbol, 'chart')}>
      <td className="num text-center text-dim">{row.rank}</td>
      <td className="whitespace-nowrap">
        <div className="flex items-center gap-2">
          <span className="text-ticker text-fg">{row.symbol}</span>
          {row.is_fno           && <Badge color="violet">F&O</Badge>}
          {row.is_watchlist     && <Badge color="amber">WL</Badge>}
          {row.is_new_watchlist && <Badge color="accent" title="New to watchlist in the last 7 days">NEW</Badge>}
          {row.bb_squeeze       && <Badge color="violet">SQ{row.squeeze_days}</Badge>}
          {row.nr7              && <Badge color="sky">NR7</Badge>}
          <LivePrice ltp={livePrice?.ltp ?? undefined} prevClose={livePrice?.prevClose ?? row.prev_day_close ?? undefined} marketOpen={marketOpen} />
        </div>
        {row.company_name && <div className="max-w-[220px] truncate text-[10px] text-ghost">{row.company_name}</div>}
      </td>
      <td className="text-right"><ScoreBar value={row.total_score}      color="accent" /></td>
      <td className="text-right"><ScoreBar value={row.momentum_score}   color="amber"  /></td>
      <td className="text-right"><ScoreBar value={row.trend_score}      color="bull"   /></td>
      <td className="text-right"><ScoreBar value={row.volatility_score} color="violet" /></td>
      <td className="text-right"><ScoreBar value={row.structure_score}  color="sky"    /></td>
      <td className="num text-right text-dim">{row.adx_14 != null ? row.adx_14.toFixed(0) : '-'}</td>
      <td className="num text-right font-bold" style={{ color: rsiColor(row.rsi_14) }}>{row.rsi_14 != null ? row.rsi_14.toFixed(0) : '-'}</td>
      <td className="num text-right text-dim">{fmtAdv(row.adv_20_cr)}</td>
      <td className="text-center"><StageBadge stage={row.stage} /></td>
      <td className="num text-right text-dim">{fmt2(row.prev_day_close)}</td>
      <td className="num text-right" title={row.comfort_interpretation ?? undefined} style={{ color: comfortColor(row.comfort_score) }}>
        {row.comfort_score != null ? row.comfort_score.toFixed(0) : '-'}
      </td>
      <td className="text-center">
        <button type="button" onClick={e => { e.stopPropagation(); onOpen(row.symbol, 'oc'); }}
          className="text-[10px] font-black text-accent opacity-0 transition-opacity group-hover:opacity-100"
          title="View option chain">OC</button>
      </td>
    </tr>
  );
}
