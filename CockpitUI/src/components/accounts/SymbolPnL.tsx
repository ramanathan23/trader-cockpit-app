'use client';

import { memo } from 'react';
import type { TradeRow } from './accountTypes';
import { money } from './accountFmt';

type Stat = { wins: number; losses: number; pnl: number; count: number };

export const SymbolPnL = memo(function SymbolPnL({ trades }: { trades: TradeRow[] }) {
  const bySymbol = new Map<string, Stat>();
  for (const t of trades) {
    const s = bySymbol.get(t.symbol) ?? { wins: 0, losses: 0, pnl: 0, count: 0 };
    bySymbol.set(t.symbol, {
      wins: s.wins + (t.pnl > 0 ? 1 : 0),
      losses: s.losses + (t.pnl < 0 ? 1 : 0),
      pnl: s.pnl + t.pnl,
      count: s.count + 1,
    });
  }
  const rows = [...bySymbol.entries()]
    .sort((a, b) => Math.abs(b[1].pnl) - Math.abs(a[1].pnl))
    .slice(0, 8);
  const maxAbs = Math.max(1, ...rows.map(([, s]) => Math.abs(s.pnl)));

  if (!rows.length) return null;
  return (
    <div>
      <div className="mb-2 text-[13px] font-black text-fg">Symbol P&L</div>
      <div className="space-y-2">
        {rows.map(([sym, s]) => (
          <div key={sym} className="grid grid-cols-[88px_1fr_56px_64px] items-center gap-2 text-[11px]">
            <span className="font-black text-fg truncate">{sym}</span>
            <div className="relative h-2 overflow-hidden rounded bg-border">
              <div
                className={`absolute top-0 h-full rounded ${s.pnl >= 0 ? 'left-0 bg-bull/60' : 'right-0 bg-bear/60'}`}
                style={{ width: `${Math.abs(s.pnl) / maxAbs * 100}%` }}
              />
            </div>
            <span className="text-right text-ghost">{s.wins}W {s.losses}L</span>
            <span className={`num text-right font-black ${s.pnl >= 0 ? 'text-bull' : 'text-bear'}`}>
              {money(s.pnl)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
});
SymbolPnL.displayName = 'SymbolPnL';
