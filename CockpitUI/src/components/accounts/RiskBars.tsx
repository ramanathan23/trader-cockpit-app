import type { DashboardAccount } from './accountTypes';
import { money } from './accountFmt';

export function RiskBars({ accounts }: { accounts: DashboardAccount[] }) {
  const max = Math.max(1, ...accounts.map(a => Math.max(Math.abs(a.net_pnl), a.open_exposure)));
  return (
    <div className="rounded-lg border border-border bg-panel p-3">
      <div className="mb-3 text-[12px] font-black text-fg">Account Risk Shape</div>
      <div className="grid gap-3">
        {accounts.map(a => (
          <div key={a.account_id}>
            <div className="mb-1 flex justify-between text-[10px] text-ghost">
              <span>{a.display_name || a.account_id}</span><span>{money(a.open_exposure)} exposure / {money(a.net_pnl)} P&L</span>
            </div>
            <div className="h-2 overflow-hidden rounded bg-border">
              <div className="h-full bg-accent" style={{ width: `${Math.min(100, a.open_exposure / max * 100)}%` }} />
            </div>
            <div className="mt-1 h-2 overflow-hidden rounded bg-border">
              <div className={`h-full ${a.net_pnl >= 0 ? 'bg-bull' : 'bg-bear'}`} style={{ width: `${Math.min(100, Math.abs(a.net_pnl) / max * 100)}%` }} />
            </div>
          </div>
        ))}
        {accounts.length === 0 && <div className="py-5 text-center text-[12px] text-ghost">No account snapshots yet.</div>}
      </div>
    </div>
  );
}
