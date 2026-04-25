'use client';

import { memo } from 'react';
import type { TradeRow } from './accountTypes';
import { money, holdMinutes, fmtHold } from './accountFmt';

function Tile({ label, value, color = 'text-fg' }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded border border-border bg-base px-3 py-2">
      <div className="label-xs mb-1">{label}</div>
      <div className={`num text-[17px] font-black ${color}`}>{value}</div>
    </div>
  );
}

export const TradeEdge = memo(function TradeEdge({ trades }: { trades: TradeRow[] }) {
  const wins = trades.filter(t => t.pnl > 0);
  const losses = trades.filter(t => t.pnl < 0);
  const grossWin = wins.reduce((s, t) => s + t.pnl, 0);
  const grossLoss = Math.abs(losses.reduce((s, t) => s + t.pnl, 0));
  const pf = grossLoss > 0 ? grossWin / grossLoss : grossWin > 0 ? 99 : 0;
  const exp = trades.length ? trades.reduce((s, t) => s + t.pnl, 0) / trades.length : 0;
  const avgWinHold = wins.length
    ? wins.reduce((s, t) => s + holdMinutes(t.entry_time, t.exit_time), 0) / wins.length : 0;
  const avgLossHold = losses.length
    ? losses.reduce((s, t) => s + holdMinutes(t.entry_time, t.exit_time), 0) / losses.length : 0;
  const fastLosses = losses.filter(t => holdMinutes(t.entry_time, t.exit_time) < 30).length;
  const holdingLosers = avgLossHold > avgWinHold + 15 && losses.length > 2;
  const pfColor = pf >= 1.5 ? 'text-bull' : pf >= 1 ? 'text-amber' : 'text-bear';

  return (
    <div>
      <div className="mb-2 text-[13px] font-black text-fg">Edge</div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Tile label="Profit Factor" value={pf === 99 ? '∞' : pf.toFixed(2)} color={pfColor} />
        <Tile label="Expectancy / Trade" value={money(exp)} color={exp >= 0 ? 'text-bull' : 'text-bear'} />
        <Tile label="Avg Winner Hold" value={fmtHold(Math.round(avgWinHold))} />
        <Tile label="Avg Loser Hold" value={fmtHold(Math.round(avgLossHold))} color={holdingLosers ? 'text-bear' : 'text-fg'} />
      </div>
      {fastLosses > 0 && (
        <div className="mt-2 rounded border border-bear/30 bg-bear/5 px-3 py-2 text-[11px] text-bear">
          {fastLosses} trade{fastLosses > 1 ? 's' : ''} stopped out in &lt;30 min — review entry quality on those setups.
        </div>
      )}
      {holdingLosers && (
        <div className="mt-2 rounded border border-warn/30 bg-warn/5 px-3 py-2 text-[11px] text-warn">
          Holding losers {fmtHold(Math.round(avgLossHold - avgWinHold))} longer than winners — cut losses faster.
        </div>
      )}
    </div>
  );
});
TradeEdge.displayName = 'TradeEdge';
