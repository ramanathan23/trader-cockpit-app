'use client';

import { memo } from 'react';
import { Badge } from '@/components/ui/Badge';
import { fmt2, fmtAdv } from '@/lib/fmt';
import { rsiColor } from '@/lib/scoreColors';
import { screenerF52hColor, screenerPctText, screenerStageColor, screenerStageLabel } from '@/lib/screenerDisplay';
import type { StockRow } from '@/domain/stocklist';
import type { NoteEntry } from '@/hooks/useNotes';
import { StockListScorePanel } from '@/components/stocklist/StockListScorePanel';
import { StockListLevels } from '@/components/stocklist/StockListLevels';
import { StockListNoteSection } from '@/components/stocklist/StockListNoteSection';
import { SetupBehaviorBadge } from './SetupBehaviorBadge';

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
      <p className="text-[12px] text-ghost">No data — run scoring pipeline to populate.</p>
      <StockListNoteSection symbol={symbol} entries={entries} onAdd={onAdd ?? noop} onDelete={onDelete ?? noop} />
    </div>
  );

  return (
    <div className="flex flex-col gap-5">
      {/* Flags strip */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[13px] font-black tracking-wide" style={{ color: screenerStageColor(row.stage) }}>
          {screenerStageLabel(row.stage)}
        </span>
        {row.is_fno         && <Badge color="violet">F&O</Badge>}
        {row.vcp_detected   && <Badge color="accent">VCP</Badge>}
        {row.rect_breakout  && <Badge color="sky">RECT BRK</Badge>}
        {row.bb_squeeze     && <Badge color="amber">BB Squeeze</Badge>}
        {row.nr7            && <Badge color="ghost">NR7</Badge>}
        {row.weekly_bias    && (
          <Badge color={row.weekly_bias === 'BULLISH' ? 'bull' : row.weekly_bias === 'BEARISH' ? 'bear' : 'ghost'}>
            {row.weekly_bias}
          </Badge>
        )}
        <SetupBehaviorBadge
          executionScore={row.execution_score}
          executionGrade={row.execution_grade}
          fakeoutRate={row.fakeout_rate}
          liquidityScore={row.liquidity_score}
        />
      </div>

      {/* Key metric strip */}
      <div className="flex flex-wrap gap-2">
        {[
          { label: 'RSI(14)', value: fmt2(row.rsi_14), color: rsiColor(row.rsi_14) },
          { label: 'ADX(14)', value: fmt2(row.adx_14), color: 'rgb(var(--fg))' },
          { label: 'ATR',     value: fmt2(row.atr_14), color: 'rgb(var(--dim))' },
          { label: 'ADV',     value: fmtAdv(row.adv_20_cr), color: 'rgb(var(--dim))' },
          { label: 'S2H%',    value: screenerPctText(row.f52h, true), color: screenerF52hColor(row.f52h) },
          ...(row.execution_score != null ? [{ label: 'EXEC', value: fmt2(row.execution_score), color: row.execution_score >= 70 ? 'rgb(var(--bull))' : row.execution_score >= 52 ? 'rgb(var(--amber))' : 'rgb(var(--bear))' }] : []),
          ...(row.fakeout_rate != null ? [{ label: 'FAKEOUT', value: `${(row.fakeout_rate * 100).toFixed(0)}%`, color: row.fakeout_rate <= 0.25 ? 'rgb(var(--bull))' : row.fakeout_rate <= 0.45 ? 'rgb(var(--amber))' : 'rgb(var(--bear))' }] : []),
          { label: 'PRICE',   value: fmt2(row.display_price ?? row.prev_day_close), color: 'rgb(var(--fg))' },
        ].map(m => (
          <div key={m.label} className="flex flex-col rounded-md border border-border/50 bg-card/60 px-3 py-2">
            <span className="label-xs mb-0.5">{m.label}</span>
            <span className="num text-[18px] font-black" style={{ color: m.color }}>{m.value}</span>
          </div>
        ))}
      </div>

      {/* Score + Levels */}
      <div className="grid grid-cols-[220px_1fr] items-start gap-4">
        <StockListScorePanel row={row} />
        <StockListLevels row={row} />
      </div>

      {/* Notes */}
      <StockListNoteSection
        symbol={symbol} entries={entries}
        onAdd={onAdd ?? noop} onDelete={onDelete ?? noop}
      />
    </div>
  );
});
SymbolModalDetails.displayName = 'SymbolModalDetails';
