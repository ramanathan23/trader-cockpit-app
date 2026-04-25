'use client';

import { memo } from 'react';
import type { TradeRow } from './accountTypes';
import { money, when, holdMinutes, fmtHold } from './accountFmt';

export const TradesTable = memo(function TradesTable({ rows, title }: { rows: TradeRow[]; title: string }) {
  return (
    <div className="rounded-lg border border-border bg-panel">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <span className="text-[13px] font-black text-fg">{title}</span>
        <span className="text-[10px] text-ghost">{rows.length} trades</span>
      </div>
      <div className="max-h-[420px] overflow-auto">
        <table className="w-full text-left text-[11px]">
          <thead className="sticky top-0 bg-card text-[10px] uppercase tracking-widest text-ghost">
            <tr>
              <th className="px-3 py-2">Symbol</th>
              <th className="px-3 py-2">Side</th>
              <th className="px-3 py-2">Entry</th>
              <th className="px-3 py-2">Exit</th>
              <th className="px-3 py-2">Hold</th>
              <th className="px-3 py-2">Qty</th>
              <th className="px-3 py-2">P&L</th>
              <th className="px-3 py-2">Ret%</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t, i) => {
              const hold = holdMinutes(t.entry_time, t.exit_time);
              const isWin = t.pnl > 0, isLoss = t.pnl < 0;
              const fastStop = isLoss && hold > 0 && hold < 30;
              return (
                <tr
                  key={`${t.account_id}-${t.symbol}-${i}`}
                  className={`border-t border-border transition-colors ${isWin ? 'bg-bull/[0.04]' : isLoss ? 'bg-bear/[0.04]' : ''}`}
                >
                  <td className="px-3 py-2 font-black text-fg">{t.symbol}</td>
                  <td className="px-3 py-2 capitalize text-dim">{t.side}</td>
                  <td className="px-3 py-2 text-ghost">{when(t.entry_time)}</td>
                  <td className="px-3 py-2 text-ghost">{when(t.exit_time)}</td>
                  <td className={`num px-3 py-2 ${fastStop ? 'font-black text-bear' : 'text-dim'}`} title={fastStop ? 'Fast stop-out' : undefined}>
                    {fmtHold(hold)}
                    {fastStop && <span className="ml-1 text-[9px]">⚡</span>}
                  </td>
                  <td className="num px-3 py-2 text-dim">{t.quantity}</td>
                  <td className={`num px-3 py-2 font-black ${isWin ? 'text-bull' : isLoss ? 'text-bear' : 'text-fg'}`}>
                    {money(t.pnl)}
                  </td>
                  <td className={`num px-3 py-2 ${t.return_pct >= 0 ? 'text-bull' : 'text-bear'}`}>
                    {t.return_pct >= 0 ? '+' : ''}{t.return_pct.toFixed(2)}%
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr><td colSpan={8} className="px-3 py-8 text-center text-ghost">No completed trades stored yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
});
TradesTable.displayName = 'TradesTable';
