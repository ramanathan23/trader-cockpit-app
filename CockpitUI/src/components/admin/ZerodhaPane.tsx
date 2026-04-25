'use client';

import { useEffect, useState } from 'react';
import type { ZerodhaAccountStatus } from './adminTypes';
import { SectionHeader } from './FullSyncPane';

export function ZerodhaPane() {
  const [accounts, setAccounts] = useState<ZerodhaAccountStatus[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    try {
      const res = await fetch('/datasync/zerodha/accounts');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setAccounts(Array.isArray(data.accounts) ? data.accounts : []);
      setMessage(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'failed to load accounts');
    }
  }

  useEffect(() => { void load(); }, []);

  return (
    <div>
      <SectionHeader
        title="Zerodha"
        caption="Account setup moved to the app rail Accounts page. This pane only shows connection status for pipeline sync."
      />
      {message && <p className="mb-4 rounded-lg border border-border bg-card px-3 py-2 text-[11px] text-dim">{message}</p>}
      <div className="rounded-lg border border-border bg-panel">
        {accounts.map(account => (
          <div key={account.account_id} className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <div className="text-[12px] font-black text-fg">{account.display_name || account.account_id}</div>
              <div className="text-[10px] text-ghost">{account.account_id} / {account.client_id}</div>
            </div>
            <span className="rounded-full border border-border px-2 py-0.5 text-[10px] font-black text-dim">
              {account.status.replace('_', ' ')}
            </span>
          </div>
        ))}
        {accounts.length === 0 && <div className="px-4 py-6 text-center text-[12px] text-ghost">No accounts configured.</div>}
      </div>
    </div>
  );
}
