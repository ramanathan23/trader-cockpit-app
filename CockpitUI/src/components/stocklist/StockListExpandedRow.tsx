'use client';

import { memo } from 'react';
import { BarChart2, Link2 } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { fmt2, fmtAdv } from '@/lib/fmt';
import { screenerF52hColor, screenerPctText } from '@/lib/screenerDisplay';
import type { StockRow } from '@/domain/stocklist';
import type { NoteEntry } from '@/hooks/useNotes';
import type { SymbolModalTab } from '@/components/dashboard/SymbolModal';
import { COL_SPAN } from './stocklistTypes';
import { StockListLevels } from './StockListLevels';
import { StockListNoteSection } from './StockListNoteSection';

interface ExpandedRowProps {
  row: StockRow; entries: NoteEntry[];
  onAdd: (s: string, t: string) => void; onDelete: (s: string, id: string) => void;
  onOpenModal: (tab: SymbolModalTab) => void;
}

function MetricTile({ label, value, color, tone = 'default' }: {
  label: string; value: string; color: string; tone?: 'default' | 'price';
}) {
  return (
    <div className={`min-w-[116px] rounded-md border px-3 py-2 ${tone === 'price' ? 'border-accent/30 bg-accent/10' : 'border-border/40 bg-base/40'}`}>
      <span className="label-xs block">{label}</span>
      <span className="num mt-1 block text-[16px] font-black leading-none" style={{ color }}>{value}</span>
    </div>
  );
}

export const StockListExpandedRow = memo(({ row, entries, onAdd, onDelete, onOpenModal }: ExpandedRowProps) => {
  const price = row.display_price ?? row.prev_day_close;
  const metrics = [
    { label: 'Price',  value: price != null ? fmt2(price) : '—', color: 'rgb(var(--fg))', tone: 'price' as const },
    { label: 'ATR',    value: row.atr_14 != null ? `Rs ${fmt2(row.atr_14)}` : '—', color: 'rgb(var(--dim))' },
    { label: 'ADV',    value: fmtAdv(row.adv_20_cr), color: 'rgb(var(--dim))' },
    { label: '52W Gap', value: screenerPctText(row.f52h, true), color: screenerF52hColor(row.f52h) },
  ];

  return (
    <tr className="bg-base/50">
      <td colSpan={COL_SPAN} className="pb-5 pt-0">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/30 bg-panel/45 px-4 py-2.5">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            {row.weekly_bias && (
              <Badge color={row.weekly_bias === 'BULLISH' ? 'bull' : row.weekly_bias === 'BEARISH' ? 'bear' : 'ghost'}>
                {row.weekly_bias}
              </Badge>
            )}
            {row.vcp_detected  && <Badge color="accent">VCP {row.vcp_contractions != null ? `${row.vcp_contractions}x` : ''}</Badge>}
            {row.rect_breakout && <Badge color="sky">RECT {row.rect_range_pct != null ? `${row.rect_range_pct.toFixed(1)}%` : ''}</Badge>}
            {row.consolidation_days != null && row.consolidation_days > 0 && <Badge color="dim">{row.consolidation_days}d consol</Badge>}
          </div>
          <div className="flex shrink-0 gap-1.5">
            <button type="button" className="icon-btn h-8 w-8" title="Open chart" onClick={() => onOpenModal('chart')}>
              <BarChart2 size={14} />
            </button>
            <button type="button" className="icon-btn h-8 w-8" title="Open option chain" onClick={() => onOpenModal('oc')}>
              <Link2 size={14} />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 border-b border-border/20 px-4 py-3 sm:grid-cols-4">
          {metrics.map(m => <MetricTile key={m.label} {...m} />)}
        </div>

        <div className="grid gap-4 px-4 pt-4 xl:grid-cols-[minmax(520px,1fr)_300px]">
          <StockListLevels row={row} />
          <StockListNoteSection symbol={row.symbol} entries={entries} onAdd={onAdd} onDelete={onDelete} />
        </div>
      </td>
    </tr>
  );
});
StockListExpandedRow.displayName = 'StockListExpandedRow';
