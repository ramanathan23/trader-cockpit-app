'use client';

import { useEffect, useState } from 'react';
import type { ScoredSymbol } from '@/domain/dashboard';
import { DailyChart } from './DailyChart';

function comfortColor(v: number | null | undefined): string {
  if (v == null) return 'rgb(var(--ghost))';
  if (v >= 80) return 'rgb(var(--bull))';
  if (v >= 65) return 'rgb(var(--accent))';
  if (v >= 50) return 'rgb(var(--amber))';
  return 'rgb(var(--bear))';
}

interface WatchlistSplitViewProps {
  scores: ScoredSymbol[];
  loading: boolean;
}

export function WatchlistSplitView({ scores, loading }: WatchlistSplitViewProps) {
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (scores.length > 0 && (!selected || !scores.find(s => s.symbol === selected))) {
      setSelected(scores[0].symbol);
    }
  }, [scores]);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center text-[13px] text-dim">
        Loading…
      </div>
    );
  }

  if (scores.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-[13px] text-dim">
        No symbols in watchlist.
      </div>
    );
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* left list */}
      <div className="flex w-60 shrink-0 flex-col overflow-y-auto border-r border-border bg-panel/50">
        {scores.map(row => {
          const isSel = selected === row.symbol;
          return (
            <button
              key={row.symbol}
              type="button"
              onClick={() => setSelected(row.symbol)}
              className={[
                'flex w-full items-center gap-2 border-b border-border/40 px-3 py-2 text-left transition-colors hover:bg-lift/50',
                isSel ? 'bg-lift border-l-2 border-l-accent' : 'border-l-2 border-l-transparent',
              ].join(' ')}
            >
              <span className="num w-5 shrink-0 text-[10px] text-ghost">{row.rank}</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1">
                  <span
                    className="text-[12px] font-black"
                    style={{ color: isSel ? 'rgb(var(--accent))' : 'rgb(var(--fg))' }}
                  >
                    {row.symbol}
                  </span>
                  {row.is_fno && (
                    <span className="text-[8px] font-black" style={{ color: 'rgb(var(--violet))' }}>F&O</span>
                  )}
                  {row.is_new_watchlist && (
                    <span className="text-[8px] font-black" style={{ color: 'rgb(var(--accent))' }}>NEW</span>
                  )}
                  {row.nr7 && (
                    <span className="text-[8px] font-black" style={{ color: 'rgb(var(--sky))' }}>NR7</span>
                  )}
                </div>
                <div className="flex items-center gap-2 font-mono text-[9px] text-ghost">
                  <span>
                    T{' '}
                    <span style={{ color: 'rgb(var(--accent))' }}>{row.total_score.toFixed(0)}</span>
                  </span>
                  {row.comfort_score != null && (
                    <span>
                      C{' '}
                      <span style={{ color: comfortColor(row.comfort_score) }}>{row.comfort_score.toFixed(0)}</span>
                    </span>
                  )}
                  <span
                    className="font-black"
                    style={{
                      color:
                        row.weekly_bias === 'BULLISH'
                          ? 'rgb(var(--bull))'
                          : row.weekly_bias === 'BEARISH'
                          ? 'rgb(var(--bear))'
                          : 'rgb(var(--ghost))',
                    }}
                  >
                    {row.weekly_bias === 'BULLISH' ? 'UP' : row.weekly_bias === 'BEARISH' ? 'DN' : '—'}
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* right chart */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {selected ? (
          <DailyChart symbol={selected} height="100%" />
        ) : (
          <div className="flex flex-1 items-center justify-center text-[13px] text-dim">
            Select a symbol
          </div>
        )}
      </div>
    </div>
  );
}
