'use client';

import { memo } from 'react';
import type { DashboardAccount } from './accountTypes';
import { money } from './accountFmt';

function Bar({ pct, color }: { pct: number; color: string }) {
  return (
    <div className="mt-1 h-1.5 overflow-hidden rounded bg-border">
      <div className={`h-full rounded transition-all ${color}`} style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
    </div>
  );
}

function Row({ label, value, pct, color, signed }: { label: string; value: number; pct: number; color: string; signed?: boolean }) {
  const valColor = signed && value !== 0 ? value >= 0 ? 'text-bull' : 'text-bear' : 'text-fg';
  return (
    <div>
      <div className="flex items-baseline justify-between text-[11px]">
        <span className="text-ghost">{label}</span>
        <span className={`num font-black ${valColor}`}>{money(value)}</span>
      </div>
      <Bar pct={pct} color={color} />
    </div>
  );
}

export const CapitalSummary = memo(function CapitalSummary({ account }: { account: DashboardAccount }) {
  const cap = Math.max(1, account.strategy_capital);
  return (
    <div className="rounded-lg border border-border bg-panel p-4">
      <div className="mb-4 text-[13px] font-black text-fg">Portfolio Breakdown</div>
      <div className="space-y-3">
        <Row label="Strategy Capital" value={account.strategy_capital} pct={100} color="bg-dim/30" />
        <Row label="Broker Net Value" value={account.broker_net} pct={account.broker_net / cap * 100} color="bg-accent/60" />
        <Row label="Open Exposure" value={account.open_exposure} pct={account.utilization_pct} color="bg-violet/55" />
        <Row label="Cash Available" value={account.cash} pct={account.cash / cap * 100} color="bg-sky/55" />
        <Row label="Realized P&L" value={account.realized_pnl} pct={Math.abs(account.realized_pnl) / cap * 100} color={account.realized_pnl >= 0 ? 'bg-bull/65' : 'bg-bear/65'} signed />
        <Row label="Unrealized P&L" value={account.unrealized_pnl} pct={Math.abs(account.unrealized_pnl) / cap * 100} color={account.unrealized_pnl >= 0 ? 'bg-bull/40' : 'bg-bear/40'} signed />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2 border-t border-border pt-3 text-[11px]">
        <div><span className="text-ghost">CE Open</span> <b className="num text-violet">{account.ce_count}</b></div>
        <div><span className="text-ghost">PE Open</span> <b className="num text-amber">{account.pe_count}</b></div>
        <div><span className="text-ghost">Concentration</span> <b className="num text-fg">{account.concentration_pct}%</b></div>
        <div><span className="text-ghost">Utilization</span> <b className={`num ${account.utilization_pct > 80 ? 'text-bear' : account.utilization_pct > 50 ? 'text-amber' : 'text-fg'}`}>{account.utilization_pct}%</b></div>
      </div>
    </div>
  );
});
CapitalSummary.displayName = 'CapitalSummary';
