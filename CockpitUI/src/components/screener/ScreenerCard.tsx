'use client';

import { memo } from 'react';
import type { ScreenerRow } from '@/domain/screener';
import { advColor } from '@/domain/signal';
import { LivePrice } from '@/components/ui/LivePrice';
import { fmtAdv } from '@/lib/fmt';
import { screenerPctColor, screenerPctText, screenerF52hColor, screenerF52lColor } from '@/lib/screenerDisplay';

function Metric({ label, title, value, color }: { label: string; title?: string; value: string; color: string }) {
  return (
    <div className="rounded-md border border-border bg-base/50 px-2 py-1.5 text-center" title={title}>
      <div className="text-[9px] font-black text-ghost">{label}</div>
      <div className="num mt-0.5 font-black" style={{ color }}>{value}</div>
    </div>
  );
}

function RangeMetric({ label, title, value, color, pct }: { label: string; title?: string; value: string; color: string; pct: number }) {
  return (
    <div title={title}>
      <div className="mb-1 flex items-center justify-between">
        <span className="font-black text-ghost">{label}</span>
        <span className="num font-black" style={{ color }}>{value}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-border">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

export const ScreenerCard = memo(({ row: r, onChart, marketOpen }: { row: ScreenerRow; onChart?: (sym: string) => void; marketOpen: boolean }) => (
  <article className="surface-card cursor-pointer p-3 transition-colors hover:bg-lift" onClick={() => onChart?.(r.symbol)}>
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="truncate text-ticker text-fg">{r.symbol}</div>
        <div className="mt-1 text-[10px] text-ghost">ATR {r.atr_14 != null ? r.atr_14.toFixed(2) : '-'}</div>
      </div>
      {r.adv_20_cr != null && <span className="chip" style={{ color: advColor(r.adv_20_cr) }}>{fmtAdv(r.adv_20_cr)}</span>}
    </div>
    <div className="mt-4 flex items-baseline justify-between gap-3">
      <LivePrice ltp={r.current_price} prevClose={r.prev_day_close} marketOpen={marketOpen} className="text-[18px]" />
      <span className="num text-[11px] font-black" style={{ color: screenerPctColor(r.week_return_pct) }}>
        WK {screenerPctText(r.week_return_pct, true)}
      </span>
    </div>
    <div className="mt-3 grid grid-cols-3 gap-2 text-[10px]">
      <Metric label="DVWAP" title="% above/below session VWAP"  value={screenerPctText(r.dvwap_delta_pct, true)}  color={screenerPctColor(r.dvwap_delta_pct)} />
      <Metric label="50E"   title="% above/below 50-day EMA"    value={screenerPctText(r.ema50_delta_pct, true)}   color={screenerPctColor(r.ema50_delta_pct)} />
      <Metric label="200E"  title="% above/below 200-day EMA"   value={screenerPctText(r.ema200_delta_pct, true)}  color={screenerPctColor(r.ema200_delta_pct)} />
    </div>
    <div className="mt-3 grid grid-cols-2 gap-2 text-[10px]">
      <RangeMetric label="52H" title="% from 52-week high (0 = at high)" value={screenerPctText(r.f52h)} color={screenerF52hColor(r.f52h)} pct={Math.min(100, Math.abs(r.f52h ?? 0))} />
      <RangeMetric label="52L" title="% above 52-week low" value={r.f52l != null ? `+${r.f52l.toFixed(1)}%` : '-'} color={screenerF52lColor(r.f52l)} pct={Math.min(100, Math.abs(r.f52l ?? 0))} />
    </div>
    <div className="mt-3 grid grid-cols-2 gap-2 text-[10px] text-ghost">
      <span>W+ <b className="num text-dim">{screenerPctText(r.week_gain_pct, true)}</b></span>
      <span>W- <b className="num text-dim">{screenerPctText(r.week_decline_pct)}</b></span>
    </div>
  </article>
));
ScreenerCard.displayName = 'ScreenerCard';
