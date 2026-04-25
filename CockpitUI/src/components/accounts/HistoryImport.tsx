'use client';

import { useState } from 'react';
import type { ZerodhaAccountStatus } from '@/components/admin/adminTypes';

export function HistoryImport({
  accounts, onImport, onPnlImport,
}: {
  accounts: ZerodhaAccountStatus[];
  onImport: (accountId: string, file: File) => Promise<boolean>;
  onPnlImport: (accountId: string, file: File) => Promise<boolean>;
}) {
  const [accountId, setAccountId] = useState('');
  const [tradebook, setTradebook] = useState<File | null>(null);
  const [pnl, setPnl] = useState<File | null>(null);
  const active = accountId || accounts[0]?.account_id || '';
  async function submitTradebook() {
    if (!active || !tradebook) return;
    if (await onImport(active, tradebook)) setTradebook(null);
  }
  async function submitPnl() {
    if (!active || !pnl) return;
    if (await onPnlImport(active, pnl)) setPnl(null);
  }
  return (
    <div className="rounded-lg border border-border bg-panel p-4">
      <h2 className="text-[13px] font-black text-fg">Historical Backfill</h2>
      <p className="mt-1 text-[11px] text-ghost">
        Import tradebook for gross trades and Console P&L statement for charges/net realized. Daily Kite sync handles deltas after this.
      </p>
      <div className="mt-3 grid gap-2">
        <select value={active} onChange={e => setAccountId(e.target.value)}
          className="rounded-lg border border-border bg-base px-3 py-2 text-[12px] text-fg">
          {accounts.map(account => <option key={account.account_id} value={account.account_id}>{account.display_name || account.account_id}</option>)}
        </select>
        <input type="file" accept=".csv,text/csv" onChange={e => setTradebook(e.target.files?.[0] ?? null)}
          className="rounded-lg border border-border bg-base px-3 py-2 text-[12px] text-fg" />
        <button type="button" onClick={() => void submitTradebook()} disabled={!active || !tradebook}
          className="rounded-lg border border-accent/50 bg-accent/10 px-4 py-2 text-[12px] font-black text-accent hover:bg-accent/20 disabled:opacity-50">
          Import Tradebook
        </button>
        <input type="file" accept=".csv,text/csv" onChange={e => setPnl(e.target.files?.[0] ?? null)}
          className="rounded-lg border border-border bg-base px-3 py-2 text-[12px] text-fg" />
        <button type="button" onClick={() => void submitPnl()} disabled={!active || !pnl}
          className="rounded-lg border border-bull/50 bg-bull/10 px-4 py-2 text-[12px] font-black text-bull hover:bg-bull/20 disabled:opacity-50">
          Import P&L Statement
        </button>
      </div>
    </div>
  );
}
