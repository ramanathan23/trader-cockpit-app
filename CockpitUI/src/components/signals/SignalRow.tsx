'use client';

import { memo } from 'react';
import { advColor, dirColor, pctColor, type Signal } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { LivePrice } from '@/components/ui/LivePrice';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/lib/cn';
import { fmt2, fmtAdv, spct, timeStr } from '@/lib/fmt';
import { SignalTypeBadge } from './SignalTypeBadge';
import { SignalNoteCell } from './SignalNoteCell';

interface SignalRowProps {
  signal: Signal;
  metrics?: InstrumentMetrics | null;
  marketOpen: boolean;
  note?: string;
  onNoteClick: (id: string) => void;
  onChart?: (sym: string) => void;
  onOptionChain?: (sym: string) => void;
}

export const SignalRow = memo(({ signal: s, metrics: m, marketOpen, note, onNoteClick, onChart, onOptionChain }: SignalRowProps) => (
  <tr className="group cursor-pointer" onClick={() => onChart?.(s.symbol)}>
    <td className="whitespace-nowrap">
      <span className="num text-[10px] text-ghost">{timeStr(s.timestamp)}</span>
    </td>
    <td className="whitespace-nowrap">
      <div className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: dirColor(s.direction) }} />
        <span className="text-ticker text-fg">{s.symbol}</span>
        {m?.is_fno  && <Badge color="violet">F&O</Badge>}
        {s._count > 1 && <Badge color="amber">{s._count}x</Badge>}
        <LivePrice ltp={m?.day_close} prevClose={m?.prev_day_close} marketOpen={marketOpen} />
      </div>
    </td>
    <td><SignalTypeBadge signalType={s.signal_type} /></td>
    <td className="text-right">
      <span className="num text-[13px] font-black text-fg">{fmt2(s.price)}</span>
    </td>
    <td className="text-right">
      {s.volume_ratio != null
        ? <span className="num font-bold text-amber">{s.volume_ratio.toFixed(1)}x</span>
        : <span className="text-ghost">-</span>}
    </td>
    <td>
      <div className="flex gap-1.5">
        {(s.bias_15m === 'BULLISH' || s.bias_15m === 'BEARISH') && (
          <span className="num text-[10px] font-black" style={{ color: dirColor(s.bias_15m) }}>
            15m {s.bias_15m === 'BULLISH' ? 'UP' : 'DN'}
          </span>
        )}
        {(s.bias_1h === 'BULLISH' || s.bias_1h === 'BEARISH') && (
          <span className="num text-[10px] font-black" style={{ color: dirColor(s.bias_1h) }}>
            1h {s.bias_1h === 'BULLISH' ? 'UP' : 'DN'}
          </span>
        )}
      </div>
    </td>
    <td className="whitespace-nowrap text-[10px] text-ghost">
      {s.entry_low != null && <span>E <b className="num text-amber">{fmt2(s.entry_low)}</b> </span>}
      {s.stop != null      && <span>SL <b className="num text-bear">{fmt2(s.stop)}</b> </span>}
      {s.target_1 != null  && <span>T1 <b className="num text-bull">{fmt2(s.target_1)}</b></span>}
    </td>
    <td className="text-right">
      {m?.adv_20_cr != null
        ? <span className="num font-bold" style={{ color: advColor(m.adv_20_cr) }}>{fmtAdv(m.adv_20_cr)}</span>
        : <span className="text-ghost">-</span>}
    </td>
    <td className="text-right">
      {m?.day_chg_pct != null
        ? <span className={cn('num font-bold', m.day_chg_pct >= 0 ? 'text-bull' : 'text-bear')}>
            {m.day_chg_pct >= 0 ? '+' : ''}{m.day_chg_pct.toFixed(2)}%
          </span>
        : <span className="text-ghost">-</span>}
    </td>
    <td className="text-right">
      {m?.week52_high && s.price != null
        ? <span className="num font-bold" style={{ color: pctColor(s.price, m.week52_high) }}>{spct(s.price, m.week52_high)}</span>
        : <span className="text-ghost">-</span>}
    </td>
    <td className="text-right" title="Signal quality score (0–100)">
      <span className="num text-dim">{s.score != null ? s.score.toFixed(0) : '-'}</span>
    </td>
    <SignalNoteCell id={s.id} symbol={s.symbol} isFno={m?.is_fno} note={note} onNoteClick={onNoteClick} onOptionChain={onOptionChain} />
  </tr>
));
SignalRow.displayName = 'SignalRow';
