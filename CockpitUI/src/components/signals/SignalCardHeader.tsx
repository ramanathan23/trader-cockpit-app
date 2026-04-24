'use client';

import { memo } from 'react';
import { dirColor, type Signal } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { LivePrice } from '@/components/ui/LivePrice';
import { Badge } from '@/components/ui/Badge';
import { fmt2, timeStr } from '@/lib/fmt';
import { BiasTag } from './BiasTag';
import { SignalTypeBadge } from './SignalTypeBadge';

interface SignalCardHeaderProps {
  signal: Signal;
  metrics?: InstrumentMetrics | null;
  marketOpen: boolean;
}

/** Top section of SignalCard — symbol identity, type badge, price, volume, MTF bias. */
export const SignalCardHeader = memo(({ signal: s, metrics: m, marketOpen }: SignalCardHeaderProps) => (
  <div className="px-3 pb-2 pt-3">
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: dirColor(s.direction) }} />
          <span className="truncate text-ticker text-fg">{s.symbol}</span>
          {s._count > 1 && <Badge color="amber">{s._count}x</Badge>}
          {m?.is_fno && <Badge color="violet">F&O</Badge>}
        </div>
        <div className="mt-0.5 flex items-center gap-2">
          <LivePrice ltp={m?.day_close} prevClose={m?.prev_day_close} marketOpen={marketOpen} />
          <span className="text-[10px] text-ghost">{timeStr(s.timestamp)}</span>
        </div>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1.5">
        <SignalTypeBadge signalType={s.signal_type} showDesc />
        {s.watchlist_conflict && (
          <span className="rounded border px-1.5 py-0.5 text-[9px] font-black uppercase tracking-wide"
            style={{ color: '#e8933a', background: 'rgba(232,147,58,0.12)', borderColor: 'rgba(232,147,58,0.35)' }}
            title="Signal direction conflicts with watchlist bias">WL≠</span>
        )}
      </div>
    </div>
    <div className="mt-4 flex items-end justify-between gap-4">
      <span className="num text-price text-fg">{fmt2(s.price)}</span>
      <div className="text-right">
        {s.volume_ratio != null && (
          <div className="num text-[12px] font-black text-amber">{s.volume_ratio.toFixed(1)}x vol</div>
        )}
        <div className="mt-1 flex justify-end gap-1.5">
          {(s.bias_15m === 'BULLISH' || s.bias_15m === 'BEARISH') && <BiasTag label="15m" bias={s.bias_15m} />}
          {(s.bias_1h === 'BULLISH' || s.bias_1h === 'BEARISH') && <BiasTag label="1h" bias={s.bias_1h} />}
        </div>
      </div>
    </div>
  </div>
));
SignalCardHeader.displayName = 'SignalCardHeader';
