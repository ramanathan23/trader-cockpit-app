'use client';

import { memo } from 'react';
import {
  advColor,
  dirColor,
  pctColor,
  signalColor,
  signalShort,
  type Signal,
} from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { LivePrice } from '@/components/ui/LivePrice';
import { fmt2, fmtAdv, spct, timeStr } from '@/lib/fmt';

interface SignalRowProps {
  signal: Signal;
  metrics?: InstrumentMetrics | null;
  marketOpen: boolean;
  note?: string;
  onNoteClick: (id: string) => void;
  onChart?: (sym: string) => void;
  onOptionChain?: (sym: string) => void;
}

export const SignalRow = memo(({ signal: s, metrics: m, marketOpen, note, onNoteClick, onChart, onOptionChain }: SignalRowProps) => {
  const color = signalColor(s.signal_type);

  return (
    <tr className="group cursor-pointer" onClick={() => onChart?.(s.symbol)}>
      <td className="whitespace-nowrap">
        <span className="num text-[10px] text-ghost">{timeStr(s.timestamp)}</span>
      </td>

      <td className="whitespace-nowrap">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: dirColor(s.direction) }} />
          <span className="text-ticker text-fg">{s.symbol}</span>
          {m?.is_fno && <span className="chip h-5 min-h-0 px-1.5" style={{ color: 'rgb(var(--violet))' }}>F&O</span>}
          {s._count > 1 && <span className="chip h-5 min-h-0 px-1.5" style={{ color: 'rgb(var(--amber))' }}>{s._count}x</span>}
          <LivePrice ltp={m?.day_close} prevClose={m?.prev_day_close} marketOpen={marketOpen} />
        </div>
      </td>

      <td>
        <span
          className="rounded-md border px-2 py-1 text-signal-badge uppercase"
          style={{ color, background: `${color}18`, borderColor: `${color}40` }}
        >
          {signalShort(s.signal_type)}
        </span>
      </td>

      <td className="text-right">
        <span className="num text-[13px] font-black text-fg">{fmt2(s.price)}</span>
      </td>

      <td className="text-right">
        {s.volume_ratio != null
          ? <span className="num font-bold" style={{ color: 'rgb(var(--amber))' }}>{s.volume_ratio.toFixed(1)}x</span>
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
        {s.entry_low != null && <span>E <b className="num" style={{ color: 'rgb(var(--amber))' }}>{fmt2(s.entry_low)}</b> </span>}
        {s.stop != null && <span>SL <b className="num" style={{ color: 'rgb(var(--bear))' }}>{fmt2(s.stop)}</b> </span>}
        {s.target_1 != null && <span>T1 <b className="num" style={{ color: 'rgb(var(--bull))' }}>{fmt2(s.target_1)}</b></span>}
      </td>

      <td className="text-right">
        {m?.adv_20_cr != null
          ? <span className="num font-bold" style={{ color: advColor(m.adv_20_cr) }}>{fmtAdv(m.adv_20_cr)}</span>
          : <span className="text-ghost">-</span>}
      </td>

      <td className="text-right">
        {m?.day_chg_pct != null
          ? <span className="num font-bold" style={{ color: m.day_chg_pct >= 0 ? 'rgb(var(--bull))' : 'rgb(var(--bear))' }}>
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

      <td>
        <div className="flex max-w-[190px] items-center gap-2">
          {m?.is_fno && (
            <button
              type="button"
              onClick={event => {
                event.stopPropagation();
                onOptionChain?.(s.symbol);
              }}
              className="text-[10px] font-black text-accent opacity-0 transition-opacity group-hover:opacity-100"
              title="View option chain"
            >
              OC
            </button>
          )}
          <button
            type="button"
            onClick={event => {
              event.stopPropagation();
              onNoteClick(s.id);
            }}
            className="text-[10px] font-bold text-ghost opacity-0 transition-opacity hover:text-fg group-hover:opacity-100"
            title={note || 'Add note'}
          >
            Note
          </button>
          {note && <span className="truncate text-[10px] text-dim" title={note}>{note}</span>}
        </div>
      </td>
    </tr>
  );
});

SignalRow.displayName = 'SignalRow';
