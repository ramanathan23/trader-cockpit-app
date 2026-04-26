'use client';

import { useState } from 'react';
import { AccountTabs } from './AccountTabs';
import { ConfigureAccounts } from './ConfigureAccounts';
import { IndividualDashboard } from './IndividualDashboard';
import { OverallDashboard } from './OverallDashboard';
import type { AccountTab } from './accountTypes';
import { useAccountsData } from './useAccountsData';

export function AccountsPanel() {
  const [tab, setTab] = useState<AccountTab>('overall');
  const { accounts, dashboard, trades, latestDayTrades, message, loading, load, saveAccount, syncNow, importHistory, importPnl } = useAccountsData();
  return (
    <section className="min-h-0 flex-1 overflow-y-auto bg-base">
      <div className="mx-auto max-w-7xl px-5 py-5">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-[18px] font-black text-fg">Accounts</h1>
            <p className="mt-1 text-[11px] text-ghost">Configure accounts, review aggregate performance, and drill into individual trade quality.</p>
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={() => void load()} className="rounded-lg border border-border px-4 py-2 text-[12px] font-black text-dim hover:bg-lift hover:text-fg">Refresh</button>
            <button type="button" onClick={() => void syncNow()} disabled={loading} className="rounded-lg border border-accent/50 bg-accent/10 px-4 py-2 text-[12px] font-black text-accent hover:bg-accent/20 disabled:opacity-50">Sync Now</button>
          </div>
        </div>
        <AccountTabs active={tab} onChange={setTab} />
        {message && <div className="mb-3 rounded-lg border border-border bg-card px-3 py-2 text-[12px] text-dim">{message}</div>}
        {dashboard?.sync_note && <div className="mb-4 rounded-lg border border-warn/30 bg-warn/10 px-3 py-2 text-[11px] text-warn">{dashboard.sync_note}</div>}
        {tab === 'configure' && (
          <ConfigureAccounts
            accounts={accounts}
            onSave={saveAccount}
            onImport={importHistory}
            onPnlImport={importPnl}
            onGenerateLinks={load}
          />
        )}
        {tab === 'overall' && <OverallDashboard dashboard={dashboard} latestDayTrades={latestDayTrades} accountStatuses={accounts} />}
        {tab === 'individual' && <IndividualDashboard dashboard={dashboard} trades={trades} accountStatuses={accounts} />}
      </div>
    </section>
  );
}
