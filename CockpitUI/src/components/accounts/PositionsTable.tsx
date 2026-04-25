import type { DashboardAccount, PositionRow } from './accountTypes';
import { money } from './accountFmt';

type Row = PositionRow & { account_id: string };

export function positionsOf(accounts: DashboardAccount[]): Row[] {
  return accounts.flatMap(a => a.open_positions.map(p => ({ ...p, account_id: a.account_id })));
}

export function PositionsTable({ rows }: { rows: Row[] }) {
  return (
    <div className="rounded-lg border border-border bg-panel">
      <div className="border-b border-border px-4 py-3 text-[13px] font-black text-fg">Open Positions</div>
      <div className="max-h-[360px] overflow-auto">
        <table className="w-full text-left text-[12px]">
          <thead className="sticky top-0 bg-card text-[10px] uppercase tracking-widest text-ghost">
            <tr><th className="px-3 py-2">Account</th><th className="px-3 py-2">Symbol</th><th className="px-3 py-2">Qty</th><th className="px-3 py-2">LTP</th><th className="px-3 py-2">P&L</th></tr>
          </thead>
          <tbody>
            {rows.map((p, i) => (
              <tr key={`${p.account_id}-${p.symbol}-${i}`} className="border-t border-border">
                <td className="px-3 py-2 text-dim">{p.account_id}</td><td className="px-3 py-2 font-black text-fg">{p.symbol}</td>
                <td className="num px-3 py-2 text-dim">{p.quantity}</td><td className="num px-3 py-2 text-dim">{p.last_price}</td>
                <td className={`num px-3 py-2 ${(p.unrealised ?? p.pnl ?? 0) >= 0 ? 'text-bull' : 'text-bear'}`}>{money(p.unrealised ?? p.pnl)}</td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={5} className="px-3 py-6 text-center text-ghost">No open positions in latest snapshot.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
