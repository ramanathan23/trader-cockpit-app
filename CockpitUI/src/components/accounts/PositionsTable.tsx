'use client';

import { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { DashboardAccount, PositionRow } from './accountTypes';
import { money } from './accountFmt';

type Row = PositionRow & { account_id: string };

export function positionsOf(accounts: DashboardAccount[]): Row[] {
  return accounts.flatMap(a => a.open_positions.map(p => ({ ...p, account_id: a.account_id })));
}

export function PositionsTable({ rows }: { rows: Row[] }) {
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 36,
    overscan: 10,
  });
  const items = virtualizer.getVirtualItems();

  return (
    <div className="rounded-lg border border-border bg-panel">
      <div className="border-b border-border px-4 py-3 text-[13px] font-black text-fg">Open Positions</div>
      <div ref={parentRef} className="max-h-[360px] overflow-auto">
        <table className="w-full text-left text-[12px]">
          <thead className="sticky top-0 bg-card text-[10px] uppercase tracking-widest text-ghost">
            <tr><th className="px-3 py-2">Account</th><th className="px-3 py-2">Symbol</th><th className="px-3 py-2">Qty</th><th className="px-3 py-2">LTP</th><th className="px-3 py-2">P&L</th></tr>
          </thead>
          <tbody>
            {items.length > 0 && <tr><td colSpan={5} style={{ height: items[0].start, padding: 0, border: 'none' }} /></tr>}
            {items.map(item => {
              const p = rows[item.index];
              const i = item.index;
              return (
              <tr key={`${p.account_id}-${p.symbol}-${i}`} className="border-t border-border">
                <td className="px-3 py-2 text-dim">{p.account_id}</td><td className="px-3 py-2 font-black text-fg">{p.symbol}</td>
                <td className="num px-3 py-2 text-dim">{p.quantity}</td><td className="num px-3 py-2 text-dim">{p.last_price}</td>
                <td className={`num px-3 py-2 ${(p.unrealised ?? p.pnl ?? 0) >= 0 ? 'text-bull' : 'text-bear'}`}>{money(p.unrealised ?? p.pnl)}</td>
              </tr>
              );
            })}
            {items.length > 0 && <tr><td colSpan={5} style={{ height: virtualizer.getTotalSize() - items[items.length - 1].end, padding: 0, border: 'none' }} /></tr>}
            {rows.length === 0 && <tr><td colSpan={5} className="px-3 py-6 text-center text-ghost">No open positions in latest snapshot.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
