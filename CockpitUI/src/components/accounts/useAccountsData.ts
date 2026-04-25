'use client';

import { useCallback, useEffect, useState } from 'react';
import type { AccountForm, AccountState } from './accountTypes';

export function useAccountsData() {
  const [state, setState] = useState<AccountState>({ accounts: [], dashboard: null, trades: [], latestDayTrades: [], message: null, loading: false });
  const patch = (next: Partial<AccountState>) => setState(prev => ({ ...prev, ...next }));

  const load = useCallback(async () => {
    patch({ loading: true });
    try {
      const [accountsRes, dashboardRes, tradesRes] = await Promise.all([
        fetch('/datasync/zerodha/accounts'), fetch('/datasync/zerodha/dashboard'), fetch('/datasync/zerodha/trades'),
      ]);
      if (!accountsRes.ok || !dashboardRes.ok || !tradesRes.ok) throw new Error('account dashboard API failed');
      const accountsData = await accountsRes.json(), dashboard = await dashboardRes.json(), tradeData = await tradesRes.json();
      patch({
        accounts: Array.isArray(accountsData.accounts) ? accountsData.accounts : [],
        dashboard, trades: Array.isArray(tradeData.trades) ? tradeData.trades : [],
        latestDayTrades: Array.isArray(tradeData.latest_day_trades) ? tradeData.latest_day_trades : [],
        message: null, loading: false,
      });
    } catch (err) {
      patch({ message: err instanceof Error ? err.message : 'failed to load accounts', loading: false });
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.data?.source !== 'zerodha-auth') return;
      patch({ message: `${event.data.accountId}: ${event.data.message}` });
      void load();
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [load]);

  async function saveAccount(form: AccountForm) {
    const res = await fetch('/datasync/zerodha/accounts', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...form, strategy_capital: form.strategy_capital ? Number(form.strategy_capital) : null }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => null);
      patch({ message: data?.detail ?? `save failed HTTP ${res.status}` });
      return false;
    }
    patch({ message: 'Account saved' });
    await load();
    return true;
  }

  async function syncNow() {
    patch({ loading: true });
    const res = await fetch('/datasync/zerodha/sync', { method: 'POST' });
    const data = await res.json().catch(() => ({}));
    patch({ message: (data.accounts ?? []).map((a: { account_id: string; status: string; orders?: number; trades?: number }) => `${a.account_id}: ${a.status} (${a.orders ?? 0}/${a.trades ?? 0})`).join(', ') || data.message || 'Sync complete' });
    await load();
  }

  async function importHistory(accountId: string, file: File) {
    return importCsv(accountId, file, '/datasync/zerodha/history/tradebook', 'historical trades imported', 'trades_imported');
  }

  async function importPnl(accountId: string, file: File) {
    if (/\.(xlsx|xlsm)$/i.test(file.name)) {
      const res = await fetch('/datasync/zerodha/history/pnl-statement-xlsx', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_id: accountId, xlsx_base64: await fileBase64(file) }),
      });
      return finishImport(res, accountId, 'P&L rows imported', 'pnl_rows_imported');
    }
    return importCsv(accountId, file, '/datasync/zerodha/history/pnl-statement', 'P&L rows imported', 'pnl_rows_imported');
  }

  async function importCsv(accountId: string, file: File, url: string, label: string, countKey: string) {
    const csvText = await file.text();
    const res = await fetch(url, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ account_id: accountId, csv_text: csvText }),
    });
    return finishImport(res, accountId, label, countKey);
  }

  async function finishImport(res: Response, accountId: string, label: string, countKey: string) {
    const data = await res.json().catch(() => ({}));
    patch({ message: res.ok ? `${data[countKey]} ${label} for ${accountId}` : data.detail ?? 'history import failed' });
    if (res.ok) await load();
    return res.ok;
  }

  return { ...state, load, saveAccount, syncNow, importHistory, importPnl };
}

async function fileBase64(file: File) {
  const bytes = new Uint8Array(await file.arrayBuffer());
  return btoa(Array.from(bytes, b => String.fromCharCode(b)).join(''));
}
