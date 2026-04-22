'use client';

import { memo, useState } from 'react';
import {
  advColor,
  dirColor,
  pctColor,
  signalColor,
  signalDesc,
  signalShort,
  type Direction,
  type Signal,
} from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { fmt2, fmtAdv, spct, timeStr } from '@/lib/fmt';

const BiasTag = memo(({ label, bias }: { label: string; bias: Direction }) => (
  <span className="num rounded border border-border bg-base/50 px-1.5 py-0.5 text-[9px] font-black" style={{ color: dirColor(bias) }}>
    {label} {bias === 'BULLISH' ? 'UP' : 'DN'}
  </span>
));
BiasTag.displayName = 'BiasTag';

const MetricCell = memo(({ label, title, children }: { label: string; title?: string; children: React.ReactNode }) => (
  <div className="min-w-0" title={title}>
    <div className="text-[9px] font-black uppercase text-ghost">{label}</div>
    <div className="num mt-0.5 truncate text-[11px] font-bold">{children}</div>
  </div>
));
MetricCell.displayName = 'MetricCell';

const LevelRow = memo(({ entry, stop, target }: {
  entry?: number | null;
  stop?: number | null;
  target?: number | null;
}) => {
  if (entry == null && stop == null && target == null) return null;

  return (
    <div className="grid grid-cols-3 gap-2 border-t border-border px-3 py-2 text-[10px] text-ghost">
      <span>E <b className="num" style={{ color: 'rgb(var(--amber))' }}>{fmt2(entry)}</b></span>
      <span>SL <b className="num" style={{ color: 'rgb(var(--bear))' }}>{fmt2(stop)}</b></span>
      <span>T1 <b className="num" style={{ color: 'rgb(var(--bull))' }}>{fmt2(target)}</b></span>
    </div>
  );
});
LevelRow.displayName = 'LevelRow';

const NoteBar = memo(({ id, note, onSave }: {
  id: string;
  note?: string;
  onSave: (id: string, text: string) => void;
}) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');

  const startEdit = () => {
    setDraft(note ?? '');
    setEditing(true);
  };

  const commit = () => {
    onSave(id, draft);
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="border-t border-border px-3 py-2" onClick={event => event.stopPropagation()}>
        <textarea
          autoFocus
          rows={2}
          value={draft}
          onChange={event => setDraft(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              commit();
            }
            if (event.key === 'Escape') setEditing(false);
          }}
          placeholder="Add a note"
          className="field min-h-[58px] w-full resize-none py-2 text-[11px]"
          style={{ colorScheme: 'inherit' }}
        />
        <div className="mt-2 flex justify-end gap-2">
          <button type="button" onClick={() => setEditing(false)} className="text-[10px] font-semibold text-ghost hover:text-fg">Cancel</button>
          <button type="button" onClick={commit} className="text-[10px] font-black text-accent">Save</button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[36px] items-center gap-2 border-t border-border px-3 py-2">
      {note ? <span className="line-clamp-2 flex-1 text-[11px] leading-snug text-dim">{note}</span> : <span className="flex-1 text-[11px] text-ghost">No note</span>}
      <button
        type="button"
        onClick={event => {
          event.stopPropagation();
          startEdit();
        }}
        className="text-[10px] font-black text-ghost hover:text-fg"
      >
        Note
      </button>
    </div>
  );
});
NoteBar.displayName = 'NoteBar';

interface SignalCardProps {
  signal: Signal;
  metrics?: InstrumentMetrics | null;
  note?: string;
  onSave: (id: string, text: string) => void;
  onChart?: (sym: string) => void;
  onOptionChain?: (sym: string) => void;
}

export const SignalCard = memo(({ signal: s, metrics: m, note, onSave, onChart, onOptionChain }: SignalCardProps) => {
  const color = signalColor(s.signal_type);
  const directionColor = dirColor(s.direction);

  return (
    <article
      className={`surface-card group relative overflow-hidden transition-colors hover:bg-lift ${s._fromCatchup ? '' : 'animate-enter pulse-new'}`}
      onClick={() => onChart?.(s.symbol)}
      title={`Open ${s.symbol} chart`}
    >
      <div className="absolute inset-x-0 top-0 h-1" style={{ background: color }} />

      <div className="px-3 pb-2 pt-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: directionColor }} />
              <span className="truncate text-ticker text-fg">{s.symbol}</span>
              {s._count > 1 && <span className="chip h-5 min-h-0 px-1.5" style={{ color: 'rgb(var(--amber))' }}>{s._count}x</span>}
              {m?.is_fno && <span className="chip h-5 min-h-0 px-1.5" style={{ color: 'rgb(var(--violet))' }}>F&O</span>}
            </div>
            <div className="mt-1 text-[10px] text-ghost">{timeStr(s.timestamp)}</div>
          </div>

          <div className="flex shrink-0 flex-col items-end gap-1.5">
            <span
              className="rounded-md border px-2 py-1 text-signal-badge uppercase"
              style={{ color, background: `${color}18`, borderColor: `${color}40` }}
              title={signalDesc(s.signal_type)}
            >
              {signalShort(s.signal_type)}
            </span>
            {s.watchlist_conflict && (
              <span
                className="rounded border px-1.5 py-0.5 text-[9px] font-black uppercase tracking-wide"
                style={{ color: '#e8933a', background: 'rgba(232,147,58,0.12)', borderColor: 'rgba(232,147,58,0.35)' }}
                title="Signal direction conflicts with watchlist bias"
              >
                WL≠
              </span>
            )}
          </div>
        </div>

        <div className="mt-4 flex items-end justify-between gap-4">
          <span className="num text-price text-fg">{fmt2(s.price)}</span>
          <div className="text-right">
            {s.volume_ratio != null && (
              <div className="num text-[12px] font-black" style={{ color: 'rgb(var(--amber))' }}>
                {s.volume_ratio.toFixed(1)}x vol
              </div>
            )}
            <div className="mt-1 flex justify-end gap-1.5">
              {(s.bias_15m === 'BULLISH' || s.bias_15m === 'BEARISH') && <BiasTag label="15m" bias={s.bias_15m} />}
              {(s.bias_1h === 'BULLISH' || s.bias_1h === 'BEARISH') && <BiasTag label="1h" bias={s.bias_1h} />}
            </div>
          </div>
        </div>
      </div>

      <LevelRow entry={s.entry_low} stop={s.stop} target={s.target_1} />

      {m && (
        <div className="grid grid-cols-3 gap-3 border-t border-border px-3 py-3">
          {m.week52_high && s.price != null && (
            <MetricCell label="52H" title="Distance from 52-week high">
              <span style={{ color: pctColor(s.price, m.week52_high) }}>{spct(s.price, m.week52_high)}</span>
            </MetricCell>
          )}
          {m.week52_low && s.price != null && (
            <MetricCell label="52L" title="Distance from 52-week low">
              <span style={{ color: pctColor(s.price, m.week52_low) }}>{spct(s.price, m.week52_low)}</span>
            </MetricCell>
          )}
          {m.atr_14 != null && (
            <MetricCell label="ATR">
              <span style={{ color: 'rgb(var(--amber))' }}>{fmt2(m.atr_14)}</span>
            </MetricCell>
          )}
          {m.adv_20_cr != null && (
            <MetricCell label="ADV">
              <span style={{ color: advColor(m.adv_20_cr) }}>{fmtAdv(m.adv_20_cr)}</span>
            </MetricCell>
          )}
          {m.day_chg_pct != null && (
            <MetricCell label="CHG%">
              <span style={{ color: m.day_chg_pct >= 0 ? 'rgb(var(--bull))' : 'rgb(var(--bear))' }}>
                {m.day_chg_pct >= 0 ? '+' : ''}{m.day_chg_pct.toFixed(2)}%
              </span>
            </MetricCell>
          )}
          {m.day_high && m.day_open && Math.abs(m.day_high - m.day_open) / m.day_open < 0.001 && (
            <MetricCell label="Open">
              <span style={{ color: 'rgb(var(--bear))' }}>O=H</span>
            </MetricCell>
          )}
          {m.day_low && m.day_open && Math.abs(m.day_open - m.day_low) / m.day_open < 0.001 && (
            <MetricCell label="Open">
              <span style={{ color: 'rgb(var(--bull))' }}>O=L</span>
            </MetricCell>
          )}
        </div>
      )}

      <div className="flex items-center justify-between border-t border-border px-3 py-2">
        <div className="flex items-center gap-2">
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
        </div>
        {s.score != null && <span className="chip num h-5 min-h-0 px-1.5">Score {s.score.toFixed(0)}</span>}
      </div>

      <NoteBar id={s.id} note={note} onSave={onSave} />
    </article>
  );
});

SignalCard.displayName = 'SignalCard';
