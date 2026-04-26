'use client';

import { memo } from 'react';
import { cn } from '@/lib/cn';
import { Badge } from '@/components/ui/Badge';
import { fmt2, fmtAdv } from '@/lib/fmt';
import { rsiColor } from '@/lib/scoreColors';
import { screenerF52hColor, screenerPctColor, screenerPctText, screenerStageColor, screenerStageLabel } from '@/lib/screenerDisplay';
import { setupTier, TIER_LABEL, TIER_TEXT_CLASS } from '@/lib/setupTier';
import type { StockRow } from '@/domain/stocklist';
import type { SymbolModalTab } from '@/components/dashboard/SymbolModal';
import type { LivePriceData } from '@/components/ui/LivePrice';
import { IntradayBadge } from '@/components/dashboard/IntradayBadge';
import { StockListRowActions } from './StockListRowActions';

interface StockListCardProps {
  row:         StockRow;
  livePrice?:  LivePriceData;
  noteCount:   number;
  onOpenModal: (tab: SymbolModalTab) => void;
}

const SCORE_COLORS = ['rgb(var(--accent))', 'rgb(var(--bull))', 'rgb(var(--amber))', 'rgb(var(--sky))'];

export const StockListCard = memo(({ row, livePrice, noteCount, onOpenModal }: StockListCardProps) => {
  const price  = livePrice?.ltp ?? row.display_price;
  const prev   = livePrice?.prevClose ?? row.prev_day_close;
  const chgPct = prev && price ? (price - prev) / prev * 100 : null;
  const tier   = setupTier(row);

  return (
    <div
      className={cn(
        'surface-card flex cursor-pointer flex-col overflow-hidden transition-all hover:shadow-md',
        tier === 'STRONG'   && 'border-bull/50',
        tier === 'BUILDING' && 'border-accent/40',
        tier === 'WATCH'    && 'border-amber/30',
      )}
      onClick={() => onOpenModal('details')}
    >
      {/* Tier stripe */}
      <div className={cn('h-1',
        tier === 'STRONG'   && 'bg-bull',
        tier === 'BUILDING' && 'bg-accent',
        tier === 'WATCH'    && 'bg-amber',
        !tier               && 'bg-border',
      )} />

      <div className="flex flex-col gap-2 p-3">
        {/* Header: symbol + tier label */}
        <div className="flex items-start justify-between gap-1">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1">
              <span className="text-ticker text-fg">{row.symbol}</span>
              {row.is_fno         && <Badge color="violet" size="sm">F&O</Badge>}
              {row.vcp_detected   && <Badge color="accent" size="sm">VCP</Badge>}
              {row.rect_breakout  && <Badge color="sky"    size="sm">RBK</Badge>}
              {row.bb_squeeze     && <Badge color="amber"  size="sm">SQZ</Badge>}
              {row.nr7            && <Badge color="ghost"  size="sm">NR7</Badge>}
            </div>
            {row.company_name && (
              <div className="mt-0.5 max-w-[160px] truncate text-[10px] text-ghost">{row.company_name}</div>
            )}
          </div>
          <div className="flex shrink-0 flex-col items-end gap-0.5">
            {tier && <span className={cn('text-[9px] font-black', TIER_TEXT_CLASS[tier])}>{TIER_LABEL[tier]}</span>}
            <span className="num text-[10px] text-ghost">#{row.rank ?? '—'}</span>
          </div>
        </div>

        {/* Price + Score */}
        <div className="flex items-end justify-between">
          <div>
            <div className="num text-[17px] font-black text-fg">{price != null ? fmt2(price) : '—'}</div>
            {chgPct != null && (
              <div className="num text-[11px]" style={{ color: screenerPctColor(chgPct) }}>
                {screenerPctText(chgPct, true)}
              </div>
            )}
          </div>
          {row.total_score != null ? (
            <div className="flex flex-col items-end">
              <span className="num text-[30px] font-black leading-none text-fg">{row.total_score.toFixed(0)}</span>
              <span className="text-[9px] text-ghost">/ 100</span>
            </div>
          ) : (
            <div className="flex items-center gap-1">
              <span className="text-[11px] font-black" style={{ color: screenerStageColor(row.stage) }}>
                {screenerStageLabel(row.stage)}
              </span>
            </div>
          )}
        </div>

        {/* Key metrics */}
        <div className="flex gap-3 text-[11px]">
          <div><div className="label-xs">RSI</div>
            <span className="num font-black" style={{ color: rsiColor(row.rsi_14) }}>{row.rsi_14 != null ? row.rsi_14.toFixed(0) : '—'}</span>
          </div>
          <div><div className="label-xs">ADX</div>
            <span className="num font-black text-dim">{row.adx_14 != null ? row.adx_14.toFixed(0) : '—'}</span>
          </div>
          <div><div className="label-xs">52H%</div>
            <span className="num font-black" style={{ color: screenerF52hColor(row.f52h) }}>{row.f52h != null ? screenerPctText(row.f52h, true) : '—'}</span>
          </div>
          <div className="ml-auto"><div className="label-xs">ADV</div>
            <span className="num font-black text-dim">{fmtAdv(row.adv_20_cr)}</span>
          </div>
        </div>

        <IntradayBadge
          sessionType={row.session_type_pred}
          issScore={row.iss_score}
          pullbackPred={row.pullback_depth_pred}
        />

        {/* Score component bars */}
        {row.total_score != null && (
          <div className="flex gap-1">
            {[row.momentum_score, row.trend_score, row.volatility_score, row.structure_score].map((v, i) => (
              <div key={i} className="h-1 flex-1 overflow-hidden rounded-full bg-border">
                <div className="h-full rounded-full" style={{ width: `${Math.min(100, v ?? 0)}%`, background: SCORE_COLORS[i] }} />
              </div>
            ))}
          </div>
        )}

        {/* Footer: stage + actions */}
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-black" style={{ color: screenerStageColor(row.stage) }}>
            {screenerStageLabel(row.stage)}
          </span>
          <StockListRowActions noteCount={noteCount} onOpenModal={onOpenModal} />
        </div>
      </div>
    </div>
  );
});
StockListCard.displayName = 'StockListCard';
