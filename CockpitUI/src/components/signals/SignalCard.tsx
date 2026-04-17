'use client';

import { memo, useState } from 'react';
import {
  dirColor, pctColor, signalColor, signalDesc, signalShort, advColor,
  type Direction, type Signal,
} from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { fmt2, fmtAdv, spct, timeStr } from '@/lib/fmt';

// ── Sub-components ────────────────────────────────────────────────────────────

const BiasTag = memo(({ label, bias }: { label: string; bias: Direction }) => {
  const c  = dirColor(bias);
  const up = bias === 'BULLISH';
  return (
    <span
      className="num text-[9px] font-bold"
      style={{ color: c }}
      title={`${label} timeframe: ${up ? 'Bullish — price above key MA, upward momentum' : 'Bearish — price below key MA, downward pressure'}`}
    >
      {label}{up ? '▲' : '▼'}
    </span>
  );
});
BiasTag.displayName = 'BiasTag';

const MetricCell = memo(({ label, title, children }: { label: string; title?: string; children: React.ReactNode }) => (
  <div className="flex flex-col gap-1" title={title}>
    <span className="text-[9px] font-bold tracking-wider uppercase text-ghost">{label}</span>
    <span className="num text-[11px] tabular-nums">{children}</span>
  </div>
));
MetricCell.displayName = 'MetricCell';

const LevelRow = memo(({ entry, stop, target }: {
  entry?: number | null; stop?: number | null; target?: number | null;
}) => {
  if (entry == null && stop == null) return null;
  return (
    <div className="flex items-center gap-3 px-3 py-2 border-t border-border text-[11px]">
      {entry  != null && <span title="Entry zone — buy in this price range" className="text-ghost">E <span className="num font-semibold" style={{ color: '#e8933a' }}>{fmt2(entry)}</span></span>}
      {stop   != null && <span title="Stop Loss — exit if price falls below this level" className="text-ghost">SL <span className="num font-semibold" style={{ color: '#f23d55' }}>{fmt2(stop)}</span></span>}
      {target != null && <span title="Target 1 — first profit-taking level" className="text-ghost">T1 <span className="num font-semibold" style={{ color: '#0dbd7d' }}>{fmt2(target)}</span></span>}
    </div>
  );
});
LevelRow.displayName = 'LevelRow';

const NoteBar = memo(({ id, note, onSave }: {
  id: string; note?: string; onSave: (id: string, text: string) => void;
}) => {
  const [editing, setEditing] = useState(false);
  const [draft,   setDraft]   = useState('');
  const startEdit = () => { setDraft(note ?? ''); setEditing(true); };
  const commit    = () => { onSave(id, draft); setEditing(false); };
  const cancel    = () => setEditing(false);

  if (editing) {
    return (
      <div className="border-t border-border px-3 py-1.5">
        <textarea
          autoFocus rows={2} value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commit(); }
            if (e.key === 'Escape') cancel();
          }}
          placeholder="Add a note…"
          className="w-full bg-base border border-border rounded text-[10px] text-fg px-1.5 py-1 resize-none focus:outline-none focus:border-accent"
          style={{ background: 'rgb(var(--base))', colorScheme: 'inherit' }}
        />
        <div className="flex gap-2 justify-end mt-1">
          <button onClick={cancel} className="text-[9px] text-ghost hover:text-dim transition-colors">cancel</button>
          <button onClick={commit} className="text-[9px] font-bold text-accent">save</button>
        </div>
      </div>
    );
  }

  return (
    <div className="border-t border-border px-3 py-2 flex items-start gap-1.5 min-h-[28px]">
      {note && <span className="text-[10px] leading-snug flex-1 break-words text-dim">{note}</span>}
      <button
        onClick={startEdit}
        className="text-[9px] shrink-0 ml-auto text-ghost hover:text-dim transition-colors"
      >
        {note ? '✎' : '+ note'}
      </button>
    </div>
  );
});
NoteBar.displayName = 'NoteBar';

// ── Main card ─────────────────────────────────────────────────────────────────

interface SignalCardProps {
  signal: Signal;
  metrics?: InstrumentMetrics | null;
  note?: string;
  onSave: (id: string, text: string) => void;
  onChart?:       (sym: string) => void;
  onOptionChain?: (sym: string) => void;
}

export const SignalCard = memo(({ signal: s, metrics: m, note, onSave, onChart, onOptionChain }: SignalCardProps) => {
  const color = signalColor(s.signal_type);
  const dc    = dirColor(s.direction);

  return (
    <div
      className={`relative flex rounded-md overflow-hidden border border-border bg-card shadow-card group${s._fromCatchup ? '' : ' animate-enter'}`}
      onClick={() => onChart?.(s.symbol)}
      style={{ cursor: 'pointer' }}
    >

      {/* Left accent stripe (3 px, signal color) */}
      <div className="w-[3px] shrink-0" style={{ background: color }} />

      {/* Card body */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* ── Header row ──────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-3 pt-3 pb-1">
          <div className="flex items-center gap-1.5 min-w-0">
            {/* Direction dot */}
            <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: dc }} />
            {/* Symbol */}
            <span className="font-bold text-[14px] tracking-wide text-fg truncate">{s.symbol}</span>
            {/* Repeat badge */}
            {s._count > 1 && (
              <span
                className="num text-[9px] font-black px-1 py-0.5 rounded-sm shrink-0"
                style={{ background: '#e8933a20', color: '#e8933a' }}
              >
                {s._count}×
              </span>
            )}
            {/* F&O badge */}
            {m?.is_fno && (
              <span className="shrink-0 text-[7px] font-black px-1 py-0.5 rounded-sm"
                    style={{ background: '#9b72f718', color: '#9b72f7' }}>F&amp;O</span>
            )}
          </div>

          {/* Signal type pill */}
          <span
            className="text-[9px] font-black tracking-[0.1em] uppercase px-1.5 py-0.5 rounded-sm shrink-0 ml-1"
            style={{ color, background: `${color}18`, border: `1px solid ${color}30` }}
            title={signalDesc(s.signal_type)}
          >
            {signalShort(s.signal_type)}
          </span>
        </div>

        {/* ── MTF bias ────────────────────────────────────────────── */}
        {(s.bias_15m === 'BULLISH' || s.bias_15m === 'BEARISH' ||
          s.bias_1h  === 'BULLISH' || s.bias_1h  === 'BEARISH') && (
          <div className="flex gap-3 px-3 pb-1.5">
            {(s.bias_15m === 'BULLISH' || s.bias_15m === 'BEARISH') && <BiasTag label="15m" bias={s.bias_15m} />}
            {(s.bias_1h  === 'BULLISH' || s.bias_1h  === 'BEARISH') && <BiasTag label="1h"  bias={s.bias_1h}  />}
          </div>
        )}

        {/* ── Hero price ──────────────────────────────────────────── */}
        <div className="flex items-baseline justify-between px-3 pb-3">
          <span
            className="num font-bold tabular-nums leading-none"
            style={{ fontSize: '20px', color: 'rgb(var(--fg))' }}
          >
            {s.price != null ? s.price.toFixed(2) : '—'}
          </span>
          {s.volume_ratio != null && (
            <span className="num text-[10px] tabular-nums text-ghost">
              Vol <span style={{ color: '#e8933a' }}>{s.volume_ratio.toFixed(1)}×</span>
            </span>
          )}
        </div>

        {/* ── Trade levels ────────────────────────────────────────── */}
        <LevelRow entry={s.entry_low} stop={s.stop} target={s.target_1} />

        {/* ── Metrics grid ────────────────────────────────────────── */}
        {m && (
          <div className="grid grid-cols-3 gap-x-3 gap-y-3 px-3 py-3 border-t border-border">
            {m.week52_high && s.price != null && (
              <MetricCell label="52H" title="% below 52-week high — 0% = at record high; negative = below high">
                <span style={{ color: pctColor(s.price, m.week52_high) }}>{spct(s.price, m.week52_high)}</span>
              </MetricCell>
            )}
            {m.week52_low && s.price != null && (
              <MetricCell label="52L" title="% above 52-week low — higher is healthier (further from lows)">
                <span style={{ color: pctColor(s.price, m.week52_low) }}>{spct(s.price, m.week52_low)}</span>
              </MetricCell>
            )}
            {m.atr_14 != null && (
              <MetricCell label="ATR" title="Average True Range (14-day) — daily volatility in price units. Use for stop sizing.">
                <span style={{ color: '#e8933a' }}>{fmt2(m.atr_14)}</span>
              </MetricCell>
            )}
            {m.adv_20_cr != null && (
              <MetricCell label="ADV" title="Avg Daily Value traded (20-day, ₹Crores) — liquidity. 5Cr=small, 25Cr=mid, 100Cr+=large cap">
                <span style={{ color: advColor(m.adv_20_cr) }}>{fmtAdv(m.adv_20_cr)}</span>
              </MetricCell>
            )}
            {m.day_chg_pct != null && (
              <MetricCell label="Δ%" title="Today's price change from previous close">
                <span style={{ color: m.day_chg_pct >= 0 ? '#0dbd7d' : '#f23d55' }}>
                  {m.day_chg_pct >= 0 ? '+' : ''}{m.day_chg_pct.toFixed(2)}%
                </span>
              </MetricCell>
            )}
            {/* O=H / O=L indicator */}
            {m.day_high && m.day_open && Math.abs(m.day_high - m.day_open) / m.day_open < 0.001 && (
              <span className="text-[8px] font-black rounded-sm px-1 py-0.5 self-center"
                style={{ background: '#f23d5520', color: '#f23d55' }}>O=H↓</span>
            )}
            {m.day_low && m.day_open && Math.abs(m.day_open - m.day_low) / m.day_open < 0.001 && (
              <span className="text-[8px] font-black rounded-sm px-1 py-0.5 self-center"
                style={{ background: '#0dbd7d20', color: '#0dbd7d' }}>O=L↑</span>
            )}
          </div>
        )}

        {/* ── Footer ──────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-3 py-2 border-t border-border">
          <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
            {m?.is_fno && (
              <button
                onClick={e => { e.stopPropagation(); onOptionChain?.(s.symbol); }}
                className="text-[9px] font-bold text-accent hover:text-fg transition-colors"
                title="View option chain">OC</button>
            )}
          </div>
          <span className="num text-[9px] tabular-nums text-ghost">{timeStr(s.timestamp)}</span>
        </div>

        <NoteBar id={s.id} note={note} onSave={onSave} />
      </div>
    </div>
  );
});

SignalCard.displayName = 'SignalCard';
