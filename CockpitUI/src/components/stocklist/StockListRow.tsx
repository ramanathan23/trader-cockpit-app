'use client';

import { memo, useCallback } from 'react';
import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Badge } from '@/components/ui/Badge';
import { fmt2, fmtAdv } from '@/lib/fmt';
import { screenerF52hColor, screenerPctColor, screenerPctText, screenerStageColor, screenerStageLabel } from '@/lib/screenerDisplay';
import type { StockRow } from '@/domain/stocklist';
import type { SymbolModalTab } from '@/components/dashboard/SymbolModal';
import { FlashPrice, type LivePriceData } from '@/components/ui/LivePrice';
import { StockListRowActions } from './StockListRowActions';

interface StockListRowProps {
  row:         StockRow;
  livePrice?:  LivePriceData;
  isExpanded:  boolean;
  noteCount:   number;
  onToggle:    (symbol: string) => void;
  onOpenModal: (symbol: string, tab: SymbolModalTab) => void;
}

export const StockListRow = memo(({ row, livePrice, isExpanded, noteCount, onToggle, onOpenModal }: StockListRowProps) => {
  const price  = livePrice?.ltp  ?? row.display_price;
  const prev   = livePrice?.prevClose ?? row.prev_day_close;
  const chgPct = prev && price ? (price - prev) / prev * 100 : null;
  const handleToggle     = useCallback(() => onToggle(row.symbol), [onToggle, row.symbol]);
  const handleOpenModal  = useCallback((tab: SymbolModalTab) => onOpenModal(row.symbol, tab), [onOpenModal, row.symbol]);

  return (
    <tr
      className={cn('group cursor-pointer border-b border-border/40 transition-colors hover:bg-lift/40',
        isExpanded && 'bg-lift/30',
      )}
      onClick={handleToggle}
    >
      <td className="w-7 px-1 py-2 text-center text-ghost">
        <ChevronRight size={11} className={cn('transition-transform duration-150', isExpanded && 'rotate-90')} />
      </td>
      <td className="py-2 pl-2 pr-4">
        <div className="flex items-center gap-1.5">
          <span className="text-ticker text-fg">{row.symbol}</span>
          {row.is_fno       && <Badge color="violet" size="sm">F&O</Badge>}
          {row.vcp_detected && <Badge color="accent" size="sm">VCP</Badge>}
          {row.rect_breakout && <Badge color="sky"   size="sm">RBK</Badge>}
        </div>
        {row.company_name && (
          <div className="mt-0.5 max-w-[150px] truncate text-[10px] text-ghost">{row.company_name}</div>
        )}
      </td>
      <td className="py-2 px-2">
        <span className="text-[11px] font-black" style={{ color: screenerStageColor(row.stage) }}>
          {screenerStageLabel(row.stage)}
        </span>
      </td>
      <td className="py-2 px-2 text-right">
        <FlashPrice price={price} prevClose={prev} className="text-[12px]" />
      </td>
      <td className="num py-2 px-2 text-right text-[11px]" style={{ color: screenerPctColor(chgPct) }}>
        {chgPct != null ? screenerPctText(chgPct, true) : '—'}
      </td>
      <td className="num py-2 px-2 text-right text-[11px] text-dim">{row.atr_14 != null ? fmt2(row.atr_14) : '—'}</td>
      <td className="num py-2 px-2 text-right text-[11px] text-dim">{fmtAdv(row.adv_20_cr)}</td>
      <td className="num py-2 px-2 text-right text-[11px]" style={{ color: screenerF52hColor(row.f52h) }}>
        {row.f52h != null ? screenerPctText(row.f52h, true) : '—'}
      </td>
      <td className="py-2 px-2" onClick={e => e.stopPropagation()}>
        <StockListRowActions noteCount={noteCount} onOpenModal={handleOpenModal} />
      </td>
    </tr>
  );
});
StockListRow.displayName = 'StockListRow';
