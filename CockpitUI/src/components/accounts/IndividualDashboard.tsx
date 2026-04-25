'use client';

import { memo, useState } from 'react';
import type { Dashboard, TradeRow } from './accountTypes';
import { statusClass, when } from './accountFmt';
import { AccountMetric } from './AccountMetric';
import { BehaviorPanel } from './BehaviorPanel';
import { CapitalSummary } from './CapitalSummary';
import { PnLCurve } from './PnLCurve';
import { positionsOf, PositionsTable } from './PositionsTable';
import { TradeBars } from './TradeBars';
import { TradesTable } from './TradesTable';

export const IndividualDashboard = memo(function IndividualDashboard({ dashboard, trades }: { dashboard: Dashboard | null; trades: TradeRow[] }) {
  const accounts = dashboard?.accounts ?? [];
  const [selected, setSelected] = useState(accounts[0]?.account_id ?? '');
  const account = accounts.find(a => a.account_id === selected) ?? accounts[0];

  if (!account) {
    return <div className="rounded-lg border border-border bg-panel p-6 text-ghost">No accounts configured.</div>;
  }

  const accountTrades = trades.filter(t => t.account_id === account.account_id);

  return (
    <div className="grid gap-4">
      {accounts.length > 1 && (
        <select value={account.account_id} onChange={e => setSelected(e.target.value)}
          className="w-fit rounded-lg border border-border bg-base px-3 py-2 text-[12px] text-fg">
          {accounts.map(a => <option key={a.account_id} value={a.account_id}>{a.display_name || a.account_id}</option>)}
        </select>
      )}

      <div className="flex items-center justify-between rounded-lg border border-border bg-panel px-4 py-3">
        <div>
          <h2 className="text-[15px] font-black text-fg">{account.display_name || account.account_id}</h2>
          <p className="text-[10px] text-ghost">Last sync {when(account.latest_sync.finished_at)} · {account.latest_sync.orders_count} orders · {account.latest_sync.trades_count} fills</p>
        </div>
        <span className={`rounded-full border px-2 py-0.5 text-[10px] font-black ${statusClass(account.latest_sync.status)}`}>
          {account.latest_sync.status}
        </span>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <AccountMetric label="Capital" value={account.strategy_capital} />
        <AccountMetric label="Net P&L" value={account.net_pnl} signed />
        <AccountMetric label="Return" value={`${account.return_pct}%`} />
        <AccountMetric label="Win Rate" value={`${account.win_rate_pct}%`} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <PnLCurve trades={accountTrades} />
        <CapitalSummary account={account} />
      </div>

      <TradeBars trades={accountTrades} />

      <BehaviorPanel account={account} trades={accountTrades} />

      <div className="grid gap-4 xl:grid-cols-[1fr_1.3fr]">
        <PositionsTable rows={account.open_positions.map(p => ({ ...p, account_id: account.account_id }))} />
        <TradesTable rows={accountTrades} title={`Stored Trades — ${account.display_name || account.account_id}`} />
      </div>
    </div>
  );
});
IndividualDashboard.displayName = 'IndividualDashboard';
