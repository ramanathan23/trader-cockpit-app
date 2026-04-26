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
import { IntradayBadge } from '@/components/dashboard/IntradayBadge';
import { COL_SPAN } from './stocklistTypes';
import { StockListScorePanel } from './StockListScorePanel';
import { StockListLevels } from './StockListLevels';
import { StockListNoteSection } from './StockListNoteSection';

interface ExpandedRowProps {
  row: StockRow; entries: NoteEntry[];
  onAdd: (s: string, t: string) => void; onDelete: (s: string, id: string) => void;
  onOpenModal: (tab: SymbolModalTab) => void;
}

function MetricTile({ label, value, color, tone = 'default' }: {
  label: string;
  value: string;
  color: string;
  tone?: 'default' | 'price';
}) {
  return (
    <div className={`min-w-[116px] rounded-md border px-3 py-2 ${tone === 'price' ? 'border-accent/30 bg-accent/10' : 'border-border/40 bg-base/40'}`}>
      <span className="label-xs block">{label}</span>
      <span className="num mt-1 block text-[16px] font-black leading-none" style={{ color }}>{value}</span>
    </div>
  );
}

export const StockListExpandedRow = memo(({ row, entries, onAdd, onDelete, onOpenModal }: ExpandedRowProps) => {
  const tier = setupTier(row);
  const price = row.display_price ?? row.prev_day_close;
  const metrics = [
    { label: 'Price', value: price != null ? fmt2(price) : '-', color: 'rgb(var(--fg))', tone: 'price' as const },
    { label: 'RSI 14', value: fmt2(row.rsi_14), color: rsiColor(row.rsi_14) },
    { label: 'ADX 14', value: fmt2(row.adx_14), color: row.adx_14 && row.adx_14 >= 20 ? 'rgb(var(--bull))' : 'rgb(var(--dim))' },
    { label: 'ATR', value: `Rs ${fmt2(row.atr_14)}`, color: 'rgb(var(--dim))' },
    { label: 'ADV', value: fmtAdv(row.adv_20_cr), color: 'rgb(var(--dim))' },
    { label: '52W Gap', value: screenerPctText(row.f52h, true), color: screenerF52hColor(row.f52h) },
    ...(row.iss_score != null ? [{ label: 'ISS', value: fmt2(row.iss_score), color: row.iss_score >= 60 ? 'rgb(var(--bull))' : row.iss_score >= 40 ? 'rgb(var(--amber))' : 'rgb(var(--bear))' }] : []),
    ...(row.comfort_score != null ? [{ label: 'Comfort', value: fmt2(row.comfort_score), color: comfortColor(row.comfort_score) }] : []),
  ];

  return (
    <tr className="bg-base/50">
      <td colSpan={COL_SPAN} className="pb-5 pt-0">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/30 bg-panel/45 px-4 py-2.5">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            {tier && (
              <span className={`text-[11px] font-black ${TIER_TEXT_CLASS[tier]}`}>{TIER_LABEL[tier]}</span>
            )}
            {row.weekly_bias && (
              <Badge color={row.weekly_bias === 'BULLISH' ? 'bull' : row.weekly_bias === 'BEARISH' ? 'bear' : 'ghost'}>
                {row.weekly_bias}
              </Badge>
            )}
            {row.vcp_detected && <Badge color="accent">VCP {row.vcp_contractions != null ? `${row.vcp_contractions}x` : ''}</Badge>}
            {row.rect_breakout && <Badge color="sky">RECT {row.rect_range_pct != null ? `${row.rect_range_pct.toFixed(1)}%` : ''}</Badge>}
            {row.bb_squeeze && <Badge color="amber">BB SQZ{row.squeeze_days != null ? ` ${row.squeeze_days}d` : ''}</Badge>}
            {row.nr7 && <Badge color="ghost">NR7</Badge>}
            {row.consolidation_days != null && <Badge color="dim">{row.consolidation_days}d consol</Badge>}
            {row.comfort_interpretation && <span className="min-w-[180px] flex-1 text-[11px] italic text-ghost">{row.comfort_interpretation}</span>}
            <IntradayBadge
              sessionType={row.session_type_pred}
              issScore={row.iss_score}
              pullbackPred={row.pullback_depth_pred}
            />
          </div>
          <div className="flex shrink-0 gap-1.5">
            <button type="button"
              className="icon-btn h-8 w-8"
              title="Open chart"
              onClick={() => onOpenModal('chart')}>
              <BarChart2 size={14} />
            </button>
            <button type="button"
              className="icon-btn h-8 w-8"
              title="Open option chain"
              onClick={() => onOpenModal('oc')}>
              <Link2 size={14} />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 border-b border-border/20 px-4 py-3 sm:grid-cols-3 lg:grid-cols-7">
          {metrics.map(m => <MetricTile key={m.label} {...m} />)}
        </div>

        <div className="grid gap-4 px-4 pt-4 xl:grid-cols-[220px_minmax(520px,1fr)_300px]">
          <StockListScorePanel row={row} />
          <StockListLevels row={row} />
          <StockListNoteSection symbol={row.symbol} entries={entries} onAdd={onAdd} onDelete={onDelete} />
        </div>
      </td>
    </tr>
  );
});
StockListExpandedRow.displayName = 'StockListExpandedRow';
