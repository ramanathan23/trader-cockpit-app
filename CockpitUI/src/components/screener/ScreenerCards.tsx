'use client';

import { memo, useCallback, useRef } from 'react';
import type { ScreenerRow } from '@/domain/screener';
import { advColor } from '@/domain/signal';
import { LivePrice } from '@/components/ui/LivePrice';
import { fmtAdv } from '@/lib/fmt';

interface ScreenerCardsProps {
  rows: ScreenerRow[];
  loading: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  onChart?: (sym: string) => void;
  marketOpen: boolean;
}

function colorForPct(value?: number | null, invert = false): string {
  if (value == null) return 'rgb(var(--ghost))';
  const score = invert ? -value : value;
  if (score >= 2) return 'rgb(var(--bull))';
  if (score >= 0) return 'rgb(var(--fg))';
  if (score >= -3) return 'rgb(var(--amber))';
  return 'rgb(var(--bear))';
}

function pctText(value?: number | null, forcePlus = false): string {
  if (value == null) return '-';
  const prefix = value > 0 || (forcePlus && value >= 0) ? '+' : '';
  return `${prefix}${value.toFixed(1)}%`;
}

const ScreenerCard = memo(({ row: r, onChart, marketOpen }: { row: ScreenerRow; onChart?: (sym: string) => void; marketOpen: boolean }) => {
  const f52hColor = r.f52h == null ? 'rgb(var(--ghost))' : r.f52h >= -2 ? 'rgb(var(--bull))' : r.f52h >= -10 ? 'rgb(var(--amber))' : 'rgb(var(--bear))';
  const f52lColor = r.f52l == null ? 'rgb(var(--ghost))' : r.f52l > 50 ? 'rgb(var(--bull))' : r.f52l > 20 ? 'rgb(var(--amber))' : r.f52l > 5 ? 'rgb(var(--fg))' : 'rgb(var(--bear))';

  return (
    <article className="surface-card p-3 transition-colors hover:bg-lift cursor-pointer" onClick={() => onChart?.(r.symbol)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-ticker text-fg">{r.symbol}</div>
          <div className="mt-1 text-[10px] text-ghost">ATR {r.atr_14 != null ? r.atr_14.toFixed(2) : '-'}</div>
        </div>
        {r.adv_20_cr != null && (
          <span className="chip" style={{ color: advColor(r.adv_20_cr) }}>{fmtAdv(r.adv_20_cr)}</span>
        )}
      </div>

      <div className="mt-4 flex items-baseline justify-between gap-3">
        <LivePrice ltp={r.current_price} prevClose={r.prev_day_close} marketOpen={marketOpen} className="text-[18px]" />
        <span className="num text-[11px] font-black" style={{ color: colorForPct(r.week_return_pct) }}>
          WK {pctText(r.week_return_pct, true)}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2 text-[10px]">
        <Metric label="DVWAP" title="% above/below session VWAP" value={pctText(r.dvwap_delta_pct, true)} color={colorForPct(r.dvwap_delta_pct)} />
        <Metric label="50E" title="% above/below 50-day EMA" value={pctText(r.ema50_delta_pct, true)} color={colorForPct(r.ema50_delta_pct)} />
        <Metric label="200E" title="% above/below 200-day EMA" value={pctText(r.ema200_delta_pct, true)} color={colorForPct(r.ema200_delta_pct)} />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-[10px]">
        <RangeMetric label="52H" title="% from 52-week high (0 = at high)" value={pctText(r.f52h)} color={f52hColor} pct={Math.min(100, Math.abs(r.f52h ?? 0))} />
        <RangeMetric label="52L" title="% above 52-week low" value={r.f52l != null ? `+${r.f52l.toFixed(1)}%` : '-'} color={f52lColor} pct={Math.min(100, Math.abs(r.f52l ?? 0))} />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-[10px] text-ghost">
        <span>W+ <b className="num text-dim">{pctText(r.week_gain_pct, true)}</b></span>
        <span>W- <b className="num text-dim">{pctText(r.week_decline_pct)}</b></span>
      </div>
    </article>
  );
});
ScreenerCard.displayName = 'ScreenerCard';

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

export const ScreenerCards = memo(({ rows, loading, hasMore, onLoadMore, onChart, marketOpen }: ScreenerCardsProps) => {
  const parentRef = useRef<HTMLDivElement>(null);

  const handleScroll = useCallback(() => {
    const el = parentRef.current;
    if (!el || loading || !hasMore || !onLoadMore) return;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 420) onLoadMore();
  }, [loading, hasMore, onLoadMore]);

  if (loading && rows.length === 0) {
    return <div className="flex flex-1 items-center justify-center text-[13px] text-dim">Loading metrics</div>;
  }

  if (rows.length === 0) {
    return <div className="flex flex-1 items-center justify-center text-[13px] text-dim">No data matches the active filters.</div>;
  }

  return (
    <div ref={parentRef} className="flex-1 overflow-y-auto p-4" onScroll={handleScroll}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        {rows.map(row => <ScreenerCard key={row.symbol} row={row} onChart={onChart} marketOpen={marketOpen} />)}
      </div>
    </div>
  );
});
ScreenerCards.displayName = 'ScreenerCards';
