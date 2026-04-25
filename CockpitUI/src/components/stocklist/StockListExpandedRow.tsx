'use client';

import { memo } from 'react';
import { BarChart2, Link2 } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { fmt2, fmtAdv } from '@/lib/fmt';
import { rsiColor, comfortColor } from '@/lib/scoreColors';
import { screenerF52hColor, screenerPctText } from '@/lib/screenerDisplay';
import { setupTier, TIER_LABEL, TIER_TEXT_CLASS } from '@/lib/setupTier';
import type { StockRow } from '@/domain/stocklist';
import type { NoteEntry } from '@/hooks/useNotes';
import type { SymbolModalTab } from '@/components/dashboard/SymbolModal';
import { COL_SPAN } from './stocklistTypes';
import { StockListScorePanel } from './StockListScorePanel';
import { StockListLevels } from './StockListLevels';
import { StockListNoteSection } from './StockListNoteSection';

interface ExpandedRowProps {
  row:         StockRow;
  entries:     NoteEntry[];
  onAdd:       (s: string, t: string) => void;
  onDelete:    (s: string, id: string) => void;
  onOpenModal: (tab: SymbolModalTab) => void;
}

export const StockListExpandedRow = memo(({ row, entries, onAdd, onDelete, onOpenModal }: ExpandedRowProps) => {
  const tier = setupTier(row);
  const price = row.display_price ?? row.prev_day_close;

  return (
    <tr className="bg-base/50">
      <td colSpan={COL_SPAN} className="pb-5 pt-0">
        {/* Setup tier + flags banner */}
        <div className="flex flex-wrap items-center gap-2 border-b border-border/30 bg-panel/40 px-4 py-2">
          {tier && (
            <span className={`text-[11px] font-black ${TIER_TEXT_CLASS[tier]}`}>{TIER_LABEL[tier]}</span>
          )}
          {row.weekly_bias && (
            <Badge color={row.weekly_bias === 'BULLISH' ? 'bull' : row.weekly_bias === 'BEARISH' ? 'bear' : 'ghost'}>
              {row.weekly_bias}
            </Badge>
          )}
          {row.vcp_detected    && <Badge color="accent">VCP {row.vcp_contractions != null ? `${row.vcp_contractions}x` : ''}</Badge>}
          {row.rect_breakout   && <Badge color="sky">RECT {row.rect_range_pct != null ? `${row.rect_range_pct.toFixed(1)}%` : ''}</Badge>}
          {row.bb_squeeze      && <Badge color="amber">BB SQZ{row.squeeze_days != null ? ` ${row.squeeze_days}d` : ''}</Badge>}
          {row.nr7             && <Badge color="ghost">NR7</Badge>}
          {row.consolidation_days != null && <Badge color="dim">{row.consolidation_days}d consol</Badge>}
          {row.comfort_interpretation && <span className="text-[11px] italic text-ghost">{row.comfort_interpretation}</span>}
        </div>

        {/* Key metrics at-a-glance strip */}
        <div className="flex flex-wrap gap-5 border-b border-border/20 px-4 py-3">
          {[
            { label: 'RSI(14)', value: fmt2(row.rsi_14),        color: rsiColor(row.rsi_14) },
            { label: 'ADX(14)', value: fmt2(row.adx_14),        color: row.adx_14 && row.adx_14 >= 20 ? 'rgb(var(--bull))' : 'rgb(var(--dim))' },
            { label: 'ATR',     value: `₹${fmt2(row.atr_14)}`,  color: 'rgb(var(--dim))' },
            { label: 'ADV',     value: fmtAdv(row.adv_20_cr),   color: 'rgb(var(--dim))' },
            { label: '52H%',    value: screenerPctText(row.f52h, true), color: screenerF52hColor(row.f52h) },
            ...(row.comfort_score != null ? [{ label: 'Comfort', value: fmt2(row.comfort_score), color: comfortColor(row.comfort_score) }] : []),
            ...(price != null ? [{ label: 'Price', value: fmt2(price), color: 'rgb(var(--fg))' }] : []),
          ].map(m => (
            <div key={m.label} className="flex flex-col">
              <span className="label-xs">{m.label}</span>
              <span className="num text-[16px] font-black" style={{ color: m.color }}>{m.value}</span>
            </div>
          ))}
        </div>

        {/* Detail grid */}
        <div className="grid grid-cols-[200px_1fr_300px] gap-6 px-4 pt-4">
          <StockListScorePanel row={row} />
          <StockListLevels row={row} />
          <StockListNoteSection symbol={row.symbol} entries={entries} onAdd={onAdd} onDelete={onDelete} />
        </div>

        {/* Quick-launch */}
        <div className="mt-4 flex gap-2 border-t border-border/30 px-4 pt-3">
          <button type="button"
            className="flex items-center gap-1.5 rounded-md border border-border bg-panel px-3 py-1.5 text-[11px] text-dim hover:border-accent/40 hover:text-accent"
            onClick={() => onOpenModal('chart')}>
            <BarChart2 size={12} /> Chart
          </button>
          <button type="button"
            className="flex items-center gap-1.5 rounded-md border border-border bg-panel px-3 py-1.5 text-[11px] text-dim hover:border-violet/40 hover:text-violet"
            onClick={() => onOpenModal('oc')}>
            <Link2 size={12} /> Option Chain
          </button>
        </div>
      </td>
    </tr>
  );
});
StockListExpandedRow.displayName = 'StockListExpandedRow';
