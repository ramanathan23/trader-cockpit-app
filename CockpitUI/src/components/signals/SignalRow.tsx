'use client';

import { memo } from 'react';
import {
  advColor, dirColor, pctColor, signalColor, signalShort,
  type InstrumentMetrics, type Signal,
} from '@/domain/signal';
import { fmt2, fmtAdv, spct, timeStr } from '@/lib/fmt';

interface SignalRowProps {
  signal: Signal;
  metrics?: InstrumentMetrics | null;
  note?: string;
  onNoteClick: (id: string) => void;
}

export const SignalRow = memo(({ signal: s, metrics: m, note, onNoteClick }: SignalRowProps) => {
  const color = signalColor(s.signal_type);

  return (
    <tr className="border-b border-border hover:bg-lift transition-colors group">
      {/* Time */}
      <td className="px-3 py-2 tabular-nums whitespace-nowrap">
        <span className="num text-[10px]" style={{ color: '#2a3f58' }}>{timeStr(s.timestamp)}</span>
      </td>

      {/* Symbol */}
      <td className="px-3 py-1.5 whitespace-nowrap">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: dirColor(s.direction) }} />
          <span className="font-bold text-[12px] tracking-wide text-fg">{s.symbol}</span>
          {s._count > 1 && (
            <span className="num text-[9px] font-black px-1 py-0.5 rounded-sm"
                  style={{ background: '#e8933a20', color: '#e8933a' }}>{s._count}×</span>
          )}
        </div>
      </td>

      {/* Signal type */}
      <td className="px-3 py-1.5">
        <span
          className="text-[8px] font-black tracking-[0.1em] uppercase px-1.5 py-0.5 rounded-sm whitespace-nowrap"
          style={{ color, background: `${color}18`, border: `1px solid ${color}28` }}
        >
          {signalShort(s.signal_type)}
        </span>
      </td>

      {/* Price */}
      <td className="px-3 py-1.5 text-right tabular-nums text-fg text-[12px] font-bold">
        <span className="num">{s.price != null ? s.price.toFixed(2) : '—'}</span>
      </td>

      {/* Volume ratio */}
      <td className="px-3 py-1.5 text-right tabular-nums text-[11px]">
        {s.volume_ratio != null
          ? <span className="num" style={{ color: '#e8933a' }}>{s.volume_ratio.toFixed(1)}×</span>
          : <span style={{ color: '#1e2e4a' }}>—</span>}
      </td>

      {/* MTF bias 15m+1h */}
      <td className="px-3 py-1.5">
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
      <td className="px-3 py-1.5 text-[10px] whitespace-nowrap" style={{ color: '#2a3f58' }}>
        {s.entry_low != null && <span>E <b className="num" style={{ color: '#e8933a' }}>{fmt2(s.entry_low)}</b> </span>}
        {s.stop      != null && <span>SL <b className="num" style={{ color: '#f23d55' }}>{fmt2(s.stop)}</b> </span>}
        {s.target_1  != null && <span>T1 <b className="num" style={{ color: '#0dbd7d' }}>{fmt2(s.target_1)}</b></span>}
      </td>

      {/* ADV */}
      <td className="px-3 py-1.5 text-right tabular-nums text-[11px]">
        {m?.adv_20_cr != null
          ? <span className="num" style={{ color: advColor(m.adv_20_cr) }}>{fmtAdv(m.adv_20_cr)}</span>
          : <span style={{ color: '#1e2e4a' }}>—</span>
        }
      </td>

      {/* Day % change */}
      <td className="px-3 py-1.5 text-right tabular-nums text-[11px] font-bold">
        {m?.day_chg_pct != null
          ? <span className="num" style={{ color: m.day_chg_pct >= 0 ? '#0dbd7d' : '#f23d55' }}>
              {m.day_chg_pct >= 0 ? '+' : ''}{m.day_chg_pct.toFixed(2)}%
            </span>
          : <span style={{ color: '#1e2e4a' }}>—</span>
        }
      </td>

      {/* 52H% */}
      <td className="px-3 py-1.5 text-right tabular-nums text-[11px]">
        {m?.week52_high && s.price != null
          ? <span className="num" style={{ color: pctColor(s.price, m.week52_high) }}>{spct(s.price, m.week52_high)}</span>
          : <span style={{ color: '#1e2e4a' }}>—</span>
        }
      </td>

      {/* Score */}
      <td className="px-3 py-1.5 text-right tabular-nums text-[11px]">
        <span className="num" style={{ color: '#2a3f58' }}>{s.score != null ? s.score.toFixed(0) : '—'}</span>
      </td>

      {/* Note */}
      <td className="px-3 py-1.5">
        <button
          onClick={() => onNoteClick(s.id)}
          className="text-[9px] transition-colors opacity-0 group-hover:opacity-100"
          style={{ color: '#2a3f58' }}
          title={note}
        >
          {note ? '✎' : '+ note'}
        </button>
        {note && (
          <span className="text-[10px] text-muted max-w-[120px] truncate block" title={note}>{note}</span>
        )}
      </td>
    </tr>
  );
});

SignalRow.displayName = 'SignalRow';
