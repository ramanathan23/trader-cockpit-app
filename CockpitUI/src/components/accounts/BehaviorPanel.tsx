'use client';

import { memo } from 'react';
import type { DashboardAccount, TradeRow } from './accountTypes';
import { money, when, holdMinutes, fmtHold } from './accountFmt';
import { TradeEdge } from './TradeEdge';
import { SymbolPnL } from './SymbolPnL';

function OpenBook({ account }: { account: DashboardAccount }) {
  const cell = (label: string, val: number, color: string) => (
    <div className="rounded border border-border bg-base px-3 py-2">
      <div className="label-xs mb-1">{label}</div>
      <div className={`num text-[17px] font-black ${color}`}>{val}</div>
    </div>
  );
  return (
    <div>
      <div className="mb-2 text-[13px] font-black text-fg">Open Book</div>
      <div className="grid grid-cols-4 gap-2">
        {cell('Winners', account.open_winners, 'text-bull')}
        {cell('Losers', account.open_losers, 'text-bear')}
        {cell('CE Open', account.ce_count, 'text-violet')}
        {cell('PE Open', account.pe_count, 'text-amber')}
      </div>
    </div>
  );
}

function Extremes({ trades }: { trades: TradeRow[] }) {
  const best = [...trades].sort((a, b) => b.pnl - a.pnl)[0];
  const worst = [...trades].sort((a, b) => a.pnl - b.pnl)[0];
  if (!best && !worst) return null;
  const card = (t: TradeRow, isBest: boolean) => {
    const hold = holdMinutes(t.entry_time, t.exit_time);
    return (
      <div className={`rounded border p-3 ${isBest ? 'border-bull/25 bg-bull/5' : 'border-bear/25 bg-bear/5'}`}>
        <div className={`label-xs mb-1 ${isBest ? 'text-bull' : 'text-bear'}`}>{isBest ? 'Best Trade' : 'Worst Trade'}</div>
        <div className="font-black text-fg">{t.symbol}</div>
        <div className="text-[10px] text-ghost">{when(t.entry_time)} · hold {fmtHold(hold)}</div>
        <div className={`num mt-1 text-[17px] font-black ${isBest ? 'text-bull' : 'text-bear'}`}>
          {isBest ? '+' : ''}{money(t.pnl)}
          <span className="ml-2 text-[12px] font-medium">
            {t.return_pct >= 0 ? '+' : ''}{t.return_pct.toFixed(2)}%
          </span>
        </div>
      </div>
    );
  };
  return (
    <div>
      <div className="mb-2 text-[13px] font-black text-fg">Extremes</div>
      <div className="grid gap-2 sm:grid-cols-2">
        {best && card(best, true)}
        {worst && card(worst, false)}
      </div>
    </div>
  );
}

export const BehaviorPanel = memo(function BehaviorPanel({ account, trades }: { account: DashboardAccount; trades: TradeRow[] }) {
  if (!trades.length) {
    return (
      <div className="rounded-lg border border-border bg-panel p-4 text-[12px] text-ghost">
        No closed trades yet. Run daily sync on trading days to build reflection history.
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-border bg-panel p-4 grid gap-6">
      <TradeEdge trades={trades} />
      <OpenBook account={account} />
      <SymbolPnL trades={trades} />
      <Extremes trades={trades} />
    </div>
  );
});
BehaviorPanel.displayName = 'BehaviorPanel';
