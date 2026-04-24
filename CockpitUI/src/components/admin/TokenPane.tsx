'use client';

import { useState } from 'react';
import type { StepStatus } from './adminTypes';
import { SectionHeader } from './FullSyncPane';

/** Form card for submitting a new Dhan access token. */
function TokenCard() {
  const [token,  setToken]  = useState('');
  const [status, setStatus] = useState<StepStatus>('idle');
  const [msg,    setMsg]    = useState<string | null>(null);

  async function submit() {
    const value = token.trim();
    if (!value || status === 'running') return;
    setStatus('running'); setMsg(null);
    try {
      const res  = await fetch('/api/v1/token', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ access_token: value }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        setStatus('error');
        setMsg(String(data?.detail ?? data?.message ?? `HTTP ${res.status}`));
        return;
      }
      setToken(''); setStatus('ok'); setMsg(data?.message ?? 'Token updated');
    } catch (err) {
      setStatus('error'); setMsg(err instanceof Error ? err.message : 'Network error');
    }
  }

  const busy        = status === 'running';
  const statusColor = status === 'ok' ? 'rgb(var(--bull))' : 'rgb(var(--bear))';

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h3 className="text-[13px] font-black text-fg">Update Dhan Token</h3>
      <p className="mt-1 text-[11px] text-ghost leading-relaxed">LiveFeed WebSocket feeds reconnect immediately on update.</p>
      <div className="mt-3 flex gap-2">
        <input
          type="password"
          value={token}
          onChange={e => setToken(e.target.value)}
          placeholder="Paste access token…"
          className="field h-8 min-w-0 flex-1 text-[12px]"
          disabled={busy}
          onKeyDown={e => { if (e.key === 'Enter') submit(); }}
        />
        <button
          type="button"
          onClick={submit}
          disabled={busy || !token.trim()}
          className={`shrink-0 rounded-lg border px-4 py-1.5 text-[12px] font-black transition-colors ${
            busy || !token.trim()
              ? 'cursor-not-allowed border-border text-ghost'
              : 'border-accent/50 bg-accent/10 text-accent hover:bg-accent/20'
          }`}
        >
          {busy ? 'Updating…' : 'Update'}
        </button>
      </div>
      {status !== 'idle' && msg && (
        <p className="mt-2 text-[10px] font-black" style={{ color: statusColor }}>{msg}</p>
      )}
    </div>
  );
}

/** Admin section: update the Dhan access token. */
export function TokenPane() {
  return (
    <div className="max-w-lg">
      <SectionHeader title="Token" caption="Update Dhan access token — LiveFeed WS reconnects immediately." />
      <TokenCard />
    </div>
  );
}
