'use client';

import { memo } from 'react';
import { Badge } from '@/components/ui/Badge';
import { fmt2, fmtAdv } from '@/lib/fmt';
import { screenerF52hColor, screenerPctColor, screenerPctText, screenerStageColor, screenerStageLabel } from '@/lib/screenerDisplay';
import type { StockRow } from '@/domain/stocklist';
import type { SymbolModalTab } from '@/components/dashboard/SymbolModal';
import { FlashPrice, type LivePriceData } from '@/components/ui/LivePrice';
import { StockListRowActions } from './StockListRowActions';

interface StockListCardProps {
  row:         StockRow;
  livePrice?:  LivePriceData;
  noteCount:   number;
  onOpenModal: (tab: SymbolModalTab) => void;
}

export const StockListCard = memo(({ row, livePrice, noteCount, onOpenModal }: StockListCardProps) => {
  const price  = livePrice?.ltp ?? row.display_price;
  const prev   = livePrice?.prevClose ?? row.prev_day_close;
  const chgPct = prev && price ? (price - prev) / prev * 100 : null;

  return (
    <div
      className="surface-card flex cursor-pointer flex-col overflow-hidden transition-all hover:shadow-md"
      onClick={() => onOpenModal('details')}
    >
      <div className="h-1 bg-border" />

      <div className="flex flex-col gap-2 p-3">
        <div className="flex items-start justify-between gap-1">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1">
              <span className="text-ticker text-fg">{row.symbol}</span>
              {row.is_fno        && <Badge color="violet" size="sm">F&O</Badge>}
              {row.vcp_detected  && <Badge color="accent" size="sm">VCP</Badge>}
              {row.rect_breakout && <Badge color="sky"    size="sm">RBK</Badge>}
            </div>
            {row.company_name && (
              <div className="mt-0.5 max-w-[160px] truncate text-[10px] text-ghost">{row.company_name}</div>
            )}
          </div>
          <span className="text-[11px] font-black" style={{ color: screenerStageColor(row.stage) }}>
            {screenerStageLabel(row.stage)}
          </span>
        </div>

        <div className="flex items-end justify-between">
          <div>
            <FlashPrice price={price} prevClose={prev} className="text-[17px]" />
            {chgPct != null && (
              <div className="num text-[11px]" style={{ color: screenerPctColor(chgPct) }}>
                {screenerPctText(chgPct, true)}
              </div>
            )}
          </div>
          <div className="flex flex-col items-end gap-1 text-[11px] text-dim">
            <span className="num">{row.atr_14 != null ? `ATR ${fmt2(row.atr_14)}` : ''}</span>
            <span className="num">{fmtAdv(row.adv_20_cr)}</span>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <span className="num text-[11px]" style={{ color: screenerF52hColor(row.f52h) }}>
            {row.f52h != null ? `52H ${screenerPctText(row.f52h, true)}` : ''}
          </span>
          <StockListRowActions noteCount={noteCount} onOpenModal={onOpenModal} />
        </div>
      </div>
    </div>
  );
});
StockListCard.displayName = 'StockListCard';
