'use client';

import { memo } from 'react';
import type { Dashboard, DashboardAccount, TradeRow } from './accountTypes';
import { money, tone } from './accountFmt';
import { AccountMetric } from './AccountMetric';
import { ActivityBars } from './ActivityBars';
import { positionsOf, PositionsTable } from './PositionsTable';
import { TradesTable } from './TradesTable';

function WinBar({ pct }: { pct: number }) {
  return (
    <div className="mt-1 h-1.5 overflow-hidden rounded bg-border">
      <div className={`h-full rounded transition-all ${pct >= 50 ? 'bg-bull' : 'bg-bear'}`} style={{ width: `${Math.min(100, pct)}%` }} />
    </div>
  );
}

function AccountCard({ a }: { a: DashboardAccount }) {
  const utilColor = a.utilization_pct > 80 ? 'text-bear' : a.utilization_pct > 50 ? 'text-amber' : 'text-fg';
  return (
    <div className="rounded-lg border border-border bg-panel p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-black text-fg">{a.display_name || a.account_id}</div>
          <div className="text-[10px] text-ghost">{a.account_id}</div>
        </div>
        <div className={`num text-[18px] font-black ${tone(a.net_pnl)}`}>{money(a.net_pnl)}</div>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-x-3 gap-y-2 text-[11px]">
        <div><span className="text-ghost">Return</span> <b className="num text-fg">{a.return_pct}%</b></div>
        <div><span className="text-ghost">Trades</span> <b className="num text-fg">{a.closed_trades}</b></div>
        <div><span className="text-ghost">Open</span> <b className="num text-fg">{a.open_positions_count}</b></div>
        <div>
          <span className="text-ghost">Win Rate</span> <b className={`num ${a.win_rate_pct >= 50 ? 'text-bull' : 'text-bear'}`}>{a.win_rate_pct}%</b>
          <WinBar pct={a.win_rate_pct} />
        </div>
        <div>
          <span className="text-ghost">Util</span> <b className={`num ${utilColor}`}>{a.utilization_pct}%</b>
          <div className="mt-1 h-1.5 overflow-hidden rounded bg-border">
            <div className="h-full rounded bg-accent/60" style={{ width: `${Math.min(100, a.utilization_pct)}%` }} />
          </div>
        </div>
        <div>
          <span className="text-ghost">W/L open</span>{' '}
          <b className="num text-bull">{a.open_winners}</b>
          <span className="text-ghost">/</span>
          <b className="num text-bear">{a.open_losers}</b>
        </div>
      </div>
    </div>
  );
}

export const OverallDashboard = memo(function OverallDashboard({ dashboard, latestDayTrades }: { dashboard: Dashboard | null; latestDayTrades: TradeRow[] }) {
  const totals = dashboard?.totals;
  return (
    <div className="grid gap-4">
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        <AccountMetric label="Strategy Capital" value={totals?.strategy_capital ?? 0} />
        <AccountMetric label="Broker Net" value={totals?.broker_net ?? 0} />
        <AccountMetric label="Realized P&L" value={totals?.realized_pnl ?? 0} signed />
        <AccountMetric label="Unrealized P&L" value={totals?.unrealized_pnl ?? 0} signed />
        <AccountMetric label="Open Exposure" value={totals?.open_exposure ?? 0} />
        <AccountMetric label="Open Positions" value={`${totals?.open_positions ?? 0}`} />
      </div>
      <ActivityBars daily={dashboard?.daily ?? []} />
      <div className="grid gap-3 md:grid-cols-2">
        {(dashboard?.accounts ?? []).map(a => <AccountCard key={a.account_id} a={a} />)}
      </div>
      <div className="grid gap-4 xl:grid-cols-[1fr_1.3fr]">
        <PositionsTable rows={positionsOf(dashboard?.accounts ?? [])} />
        <TradesTable rows={latestDayTrades} title="Trades: Today or Last Trade Day" />
      </div>
    </div>
  );
});
OverallDashboard.displayName = 'OverallDashboard';
