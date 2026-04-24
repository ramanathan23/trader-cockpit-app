'use client';

import { memo } from 'react';
import { signalColor, type Signal } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { SignalCardHeader } from './SignalCardHeader';
import { SignalCardMetrics } from './SignalCardMetrics';
import { LevelRow } from './LevelRow';
import { NoteBar } from './NoteBar';

interface SignalCardProps {
  signal: Signal;
  metrics?: InstrumentMetrics | null;
  marketOpen: boolean;
  note?: string;
  onSave: (id: string, text: string) => void;
  onChart?: (sym: string) => void;
  onOptionChain?: (sym: string) => void;
}

export const SignalCard = memo(({ signal: s, metrics: m, marketOpen, note, onSave, onChart, onOptionChain }: SignalCardProps) => {
  const color = signalColor(s.signal_type);
  return (
    <article
      className={`surface-card group relative overflow-hidden transition-colors hover:bg-lift ${s._fromCatchup ? '' : 'animate-enter pulse-new'}`}
      onClick={() => onChart?.(s.symbol)}
      title={`Open ${s.symbol} chart`}
    >
      <div className="absolute inset-x-0 top-0 h-1" style={{ background: color }} />
      <SignalCardHeader signal={s} metrics={m} marketOpen={marketOpen} />
      <LevelRow entry={s.entry_low} stop={s.stop} target={s.target_1} />
      {m && <SignalCardMetrics signal={s} metrics={m} />}

      <div className="flex items-center justify-between border-t border-border px-3 py-2">
        <div className="flex items-center gap-2">
          {m?.is_fno && (
            <button type="button"
              onClick={e => { e.stopPropagation(); onOptionChain?.(s.symbol); }}
              className="text-[10px] font-black text-accent opacity-0 transition-opacity group-hover:opacity-100"
              title="View option chain">OC</button>
          )}
        </div>
        {s.score != null && (
          <span className="chip num h-5 min-h-0 px-1.5" title="Signal quality score (0–100)">
            Score {s.score.toFixed(0)}
          </span>
        )}
      </div>

      <NoteBar id={s.id} note={note} onSave={onSave} />
    </article>
  );
});
SignalCard.displayName = 'SignalCard';
