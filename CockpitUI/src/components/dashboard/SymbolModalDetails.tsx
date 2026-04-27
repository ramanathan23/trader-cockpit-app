'use client';

import { memo } from 'react';
import { Badge } from '@/components/ui/Badge';
import { fmt2, fmtAdv } from '@/lib/fmt';
import { screenerF52hColor, screenerPctText, screenerStageColor, screenerStageLabel } from '@/lib/screenerDisplay';
import type { StockRow } from '@/domain/stocklist';
import type { NoteEntry } from '@/hooks/useNotes';
import { StockListScorePanel } from '@/components/stocklist/StockListScorePanel';
import { StockListLevels } from '@/components/stocklist/StockListLevels';
import { StockListNoteSection } from '@/components/stocklist/StockListNoteSection';

interface DetailsProps {
  symbol:    string;
  row?:      StockRow;
  entries:   NoteEntry[];
  onAdd?:    (s: string, t: string) => void;
  onDelete?: (s: string, id: string) => void;
}

export const SymbolModalDetails = memo(({ symbol, row, entries, onAdd, onDelete }: DetailsProps) => {
  const noop = () => {};
  if (!row) return (
    <div className="flex flex-col gap-4">
      <p className="text-[12px] text-ghost">No data available.</p>
      <StockListNoteSection symbol={symbol} entries={entries} onAdd={onAdd ?? noop} onDelete={onDelete ?? noop} />
    </div>
  );

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[13px] font-black tracking-wide" style={{ color: screenerStageColor(row.stage) }}>
          {screenerStageLabel(row.stage)}
        </span>
        {row.is_fno        && <Badge color="violet">F&O</Badge>}
        {row.vcp_detected  && <Badge color="accent">VCP</Badge>}
        {row.rect_breakout && <Badge color="sky">RECT BRK</Badge>}
        {row.weekly_bias   && (
          <Badge color={row.weekly_bias === 'BULLISH' ? 'bull' : row.weekly_bias === 'BEARISH' ? 'bear' : 'ghost'}>
            {row.weekly_bias}
          </Badge>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {[
          { label: 'ATR',   value: fmt2(row.atr_14),                              color: 'rgb(var(--dim))' },
          { label: 'ADV',   value: fmtAdv(row.adv_20_cr),                         color: 'rgb(var(--dim))' },
          { label: '52H%',  value: screenerPctText(row.f52h, true),                color: screenerF52hColor(row.f52h) },
          { label: 'PRICE', value: fmt2(row.display_price ?? row.prev_day_close),  color: 'rgb(var(--fg))' },
        ].map(m => (
          <div key={m.label} className="flex flex-col rounded-md border border-border/50 bg-card/60 px-3 py-2">
            <span className="label-xs mb-0.5">{m.label}</span>
            <span className="num text-[18px] font-black" style={{ color: m.color }}>{m.value}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-[220px_1fr] items-start gap-4">
        <StockListScorePanel row={row} />
        <StockListLevels row={row} />
      </div>

      <StockListNoteSection
        symbol={symbol} entries={entries}
        onAdd={onAdd ?? noop} onDelete={onDelete ?? noop}
      />
    </div>
  );
});
SymbolModalDetails.displayName = 'SymbolModalDetails';
