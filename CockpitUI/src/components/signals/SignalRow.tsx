'use client';

import { memo } from 'react';
import {
  advColor, dirColor, pctColor, signalColor, signalShort,
  type Signal,
} from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { fmt2, fmtAdv, spct, timeStr } from '@/lib/fmt';

interface SignalRowProps {
  signal: Signal;
  metrics?: InstrumentMetrics | null;
  note?: string;
  onNoteClick:    (id: string) => void;
  onChart?:       (sym: string) => void;
  onOptionChain?: (sym: string) => void;
}

export const SignalRow = memo(({ signal: s, metrics: m, note, onNoteClick, onChart, onOptionChain }: SignalRowProps) => {
  const color = signalColor(s.signal_type);

  return (
    <tr className="border-b border-border hover:bg-lift transition-colors group cursor-pointer"
        style={{ height: '36px' }}
        onClick={() => onChart?.(s.symbol)}>
      {/* Time */}
      <td className="px-2.5 py-1.5 tabular-nums whitespace-nowrap">
        <span className="num text-[10px] text-ghost">{timeStr(s.timestamp)}</span>
      </td>

      {/* Symbol */}
      <td className="px-2.5 py-1 whitespace-nowrap">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: dirColor(s.direction) }} />
          <span className="text-ticker text-fg">{s.symbol}</span>
          {m?.is_fno && (
            <span className="text-[7px] font-black px-1 py-0.5 rounded-sm"
                  style={{ background: '#9b72f718', color: '#9b72f7' }}>F&amp;O</span>
          )}
          {s._count > 1 && (
            <span className="num text-[9px] font-black px-1 py-0.5 rounded-sm"
                  style={{ background: '#e8933a20', color: '#e8933a' }}>{s._count}×</span>
          )}
        </div>
      </td>

      {/* Signal type */}
      <td className="px-2.5 py-1">
        <span
          className="text-signal-badge uppercase px-1.5 py-0.5 rounded whitespace-nowrap"
          style={{ color, background: `${color}20`, border: `1px solid ${color}35` }}
        >
          {signalShort(s.signal_type)}
        </span>
      </td>

      {/* Price */}
      <td className="px-2.5 py-1 text-right tabular-nums text-fg font-bold">
        <span className="num text-[13px]">{s.price != null ? s.price.toFixed(2) : '—'}</span>
      </td>

      {/* Volume ratio */}
      <td className="px-2.5 py-1 text-right tabular-nums text-[11px]">
        {s.volume_ratio != null
          ? <span className="num" style={{ color: '#e8933a' }}>{s.volume_ratio.toFixed(1)}×</span>
          : <span className="text-ghost">—</span>}
      </td>

      {/* MTF bias 15m+1h */}
      <td className="px-2.5 py-1">
        <div className="flex gap-1.5">
          {(s.bias_15m === 'BULLISH' || s.bias_15m === 'BEARISH') && (
            <span className="num text-[9px] font-bold" style={{ color: dirColor(s.bias_15m) }}>
              15m{s.bias_15m === 'BULLISH' ? '▲' : '▼'}
            </span>
          )}
          {(s.bias_1h === 'BULLISH' || s.bias_1h === 'BEARISH') && (
            <span className="num text-[9px] font-bold" style={{ color: dirColor(s.bias_1h) }}>
              1h{s.bias_1h === 'BULLISH' ? '▲' : '▼'}
            </span>
          )}
        </div>
      </td>

      {/* Entry / SL / T1 */}
      <td className="px-2.5 py-1 text-[10px] whitespace-nowrap text-ghost">
        {s.entry_low != null && <span>E <b className="num" style={{ color: '#e8933a' }}>{fmt2(s.entry_low)}</b> </span>}
        {s.stop      != null && <span>SL <b className="num" style={{ color: '#f23d55' }}>{fmt2(s.stop)}</b> </span>}
        {s.target_1  != null && <span>T1 <b className="num" style={{ color: '#0dbd7d' }}>{fmt2(s.target_1)}</b></span>}
      </td>

      {/* ADV */}
      <td className="px-2.5 py-1 text-right tabular-nums text-[11px]">
        {m?.adv_20_cr != null
          ? <span className="num" style={{ color: advColor(m.adv_20_cr) }}>{fmtAdv(m.adv_20_cr)}</span>
          : <span className="text-ghost">—</span>
        }
      </td>

      {/* Day % change */}
      <td className="px-2.5 py-1 text-right tabular-nums text-[11px] font-bold">
        {m?.day_chg_pct != null
          ? <span className="num" style={{ color: m.day_chg_pct >= 0 ? '#0dbd7d' : '#f23d55' }}>
              {m.day_chg_pct >= 0 ? '+' : ''}{m.day_chg_pct.toFixed(2)}%
            </span>
          : <span className="text-ghost">—</span>
        }
      </td>

      {/* 52H% */}
      <td className="px-2.5 py-1 text-right tabular-nums text-[11px]">
        {m?.week52_high && s.price != null
          ? <span className="num" style={{ color: pctColor(s.price, m.week52_high) }}>{spct(s.price, m.week52_high)}</span>
          : <span className="text-ghost">—</span>
        }
      </td>

      {/* Score */}
      <td className="px-2.5 py-1 text-right tabular-nums text-[11px]">
        <span className="num text-ghost">{s.score != null ? s.score.toFixed(0) : '—'}</span>
      </td>

      {/* Note */}
      <td className="px-2.5 py-1">
        <div className="flex items-center gap-2">
          {m?.is_fno && (
            <button
              onClick={e => { e.stopPropagation(); onOptionChain?.(s.symbol); }}
              className="text-[9px] font-bold text-accent hover:text-fg transition-colors opacity-0 group-hover:opacity-100"
              title="View option chain">OC</button>
          )}
          <button
            onClick={e => { e.stopPropagation(); onNoteClick(s.id); }}
            className="text-[9px] transition-colors opacity-0 group-hover:opacity-100"
            style={{ color: 'rgb(var(--ghost))' }}
            title={note}
          >
            {note ? '✎' : '+ note'}
          </button>
          {note && (
            <span className="text-[10px] text-dim max-w-[120px] truncate block" title={note}>{note}</span>
          )}
        </div>
      </td>
    </tr>
  );
});

SignalRow.displayName = 'SignalRow';
