'use client';

import { useState } from 'react';
import type { ZerodhaAccountStatus } from '@/components/admin/adminTypes';
import { EMPTY_FORM, type AccountForm } from './accountTypes';
import { statusClass } from './accountFmt';
import { HistoryImport } from './HistoryImport';
import { AccountLoginLink, needsLogin } from './AccountLoginLink';

const FIELDS: [keyof AccountForm, string, string][] = [
  ['account_id', 'Account ID', 'text'], ['client_id', 'Client ID', 'text'],
  ['display_name', 'Display Name', 'text'], ['api_key', 'API Key', 'text'],
  ['api_secret', 'API Secret', 'password'], ['strategy_capital', 'Strategy Capital', 'number'],
];

export function ConfigureAccounts({
  accounts, onSave, onImport, onPnlImport, onGenerateLinks,
}: {
  accounts: ZerodhaAccountStatus[];
  onSave: (form: AccountForm) => Promise<boolean>;
  onImport: (accountId: string, file: File) => Promise<boolean>;
  onPnlImport: (accountId: string, file: File) => Promise<boolean>;
  onGenerateLinks: () => Promise<void>;
}) {
  const [form, setForm] = useState<AccountForm>(EMPTY_FORM);
  const [showLinks, setShowLinks] = useState(false);
  async function save() {
    if (await onSave(form)) setForm(EMPTY_FORM);
  }
  async function generateLinks() {
    await onGenerateLinks();
    setShowLinks(true);
  }
  return (
    <div className="grid gap-4 xl:grid-cols-[370px_1fr]">
      <div className="grid gap-4">
        <div className="rounded-lg border border-border bg-panel p-4">
          <h2 className="text-[13px] font-black text-fg">Add / Update Account</h2>
          <div className="mt-3 grid gap-2">
          {FIELDS.map(([key, label, type]) => (
            <label key={key} className="block">
              <span className="mb-1 block text-[10px] font-black uppercase tracking-widest text-ghost">{label}</span>
              <input value={form[key]} type={type} onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
                className="w-full rounded-lg border border-border bg-base px-3 py-2 text-[12px] text-fg outline-none focus:border-accent" />
            </label>
          ))}
            <button type="button" onClick={() => void save()} className="mt-1 rounded-lg border border-accent/50 bg-accent/10 px-4 py-2 text-[12px] font-black text-accent hover:bg-accent/20">Save Account</button>
          </div>
        </div>
      <HistoryImport accounts={accounts} onImport={onImport} onPnlImport={onPnlImport} />
      </div>
      <div className="rounded-lg border border-border bg-panel">
        <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div className="text-[13px] font-black text-fg">Configured Accounts</div>
          <button
            type="button"
            onClick={() => void generateLinks()}
            className="rounded-lg border border-accent/40 bg-accent/10 px-3 py-1.5 text-[11px] font-black text-accent hover:bg-accent/20"
          >
            Generate Links
          </button>
        </div>
        {accounts.map(a => (
          <div key={a.account_id} className="border-b border-border px-4 py-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-black text-fg">{a.display_name || a.account_id}</div>
                <div className="text-[10px] text-ghost">{a.account_id} / {a.client_id}</div>
              </div>
              <span className={`rounded-full border px-2 py-0.5 text-[10px] font-black ${statusClass(a.status)}`}>{a.status.replace('_', ' ')}</span>
            </div>
            <AccountLoginLink account={a} showUrl={showLinks || needsLogin(a)} />
          </div>
        ))}
      </div>
    </div>
  );
}
