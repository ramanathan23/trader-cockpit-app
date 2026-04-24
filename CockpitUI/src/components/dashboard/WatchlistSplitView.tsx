'use client';

import { useEffect, useState } from 'react';
import type { ScoredSymbol } from '@/domain/dashboard';
import type { LivePriceData } from '@/components/ui/LivePrice';
import { WatchlistItem } from './WatchlistItem';
import { DailyChart } from './DailyChart';

interface WatchlistSplitViewProps {
  scores: ScoredSymbol[];
  loading: boolean;
  marketOpen: boolean;
  livePrices: Record<string, LivePriceData>;
}

export function WatchlistSplitView({ scores, loading, marketOpen, livePrices }: WatchlistSplitViewProps) {
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (scores.length > 0 && (!selected || !scores.find(s => s.symbol === selected))) {
      setSelected(scores[0].symbol);
    }
  }, [scores]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return <div className="flex flex-1 items-center justify-center text-[13px] text-dim">Loading…</div>;
  }
  if (scores.length === 0) {
    return <div className="flex flex-1 items-center justify-center text-[13px] text-dim">No symbols in watchlist.</div>;
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      <div className="flex w-60 shrink-0 flex-col overflow-y-auto border-r border-border bg-panel/50">
        {scores.map(row => (
          <WatchlistItem
            key={row.symbol}
            row={row}
            selected={selected === row.symbol}
            livePrice={livePrices[row.symbol]}
            marketOpen={marketOpen}
            onSelect={setSelected}
          />
        ))}
      </div>
      <div className="flex flex-1 flex-col overflow-hidden">
        {selected
          ? <DailyChart symbol={selected} height="100%" />
          : <div className="flex flex-1 items-center justify-center text-[13px] text-dim">Select a symbol</div>}
      </div>
    </div>
  );
}
