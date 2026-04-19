'use client';

import { useState } from 'react';

type ActionKey = 'sync-daily' | 'sync-1min' | 'compute-scores';
type ActionStatus = 'idle' | 'running' | 'ok' | 'error';

interface ActionState {
  status: ActionStatus;
  message: string | null;
}

interface Action {
  key: ActionKey;
  label: string;
  caption: string;
  endpoint: string;
  method: string;
}

const ACTIONS: Action[] = [
  {
    key: 'sync-daily',
    label: 'Sync Daily Data',
    caption: 'Fetch OHLCV from yfinance for all symbols. Auto-classifies and fills gaps.',
    endpoint: '/datasync/sync/run',
    method: 'POST',
  },
  {
    key: 'sync-1min',
    label: 'Sync 1-Min Data',
    caption: 'Fetch 1-min OHLCV from Dhan for all F&O stocks (last 90 days).',
    endpoint: '/datasync/sync/run-1min',
    method: 'POST',
  },
  {
    key: 'compute-scores',
    label: 'Compute Momentum Scores',
    caption: 'Run unified daily momentum scoring for all symbols.',
    endpoint: '/scorer/scores/compute',
    method: 'POST',
  },
];

function StatusBadge({ status, message }: { status: ActionStatus; message: string | null }) {
  if (status === 'idle') return null;

  const color =
    status === 'running' ? 'rgb(var(--amber))' :
    status === 'ok'      ? 'rgb(var(--bull))' :
                           'rgb(var(--bear))';

  const label =
    status === 'running' ? 'Running…' :
    status === 'ok'      ? 'Started' :
                           'Failed';

  return (
    <div className="mt-3 flex items-start gap-2 rounded-md border border-border bg-base/60 px-3 py-2">
      <span
        className={`mt-0.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full ${status === 'running' ? 'animate-blink' : ''}`}
        style={{ backgroundColor: color }}
      />
      <div>
        <span className="num text-[11px] font-black" style={{ color }}>{label}</span>
        {message && (
          <p className="mt-0.5 text-[10px] text-ghost">{message}</p>
        )}
      </div>
    </div>
  );
}

function ActionCard({ action }: { action: Action }) {
  const [state, setState] = useState<ActionState>({ status: 'idle', message: null });

  async function run() {
    if (state.status === 'running') return;
    setState({ status: 'running', message: null });
    try {
      const res = await fetch(action.endpoint, { method: action.method });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        const detail = data?.detail ?? data?.message ?? `HTTP ${res.status}`;
        setState({ status: 'error', message: String(detail) });
        return;
      }
      const msg = data?.message ?? data?.status ?? 'OK';
      setState({ status: 'ok', message: String(msg) });
    } catch (err) {
      setState({ status: 'error', message: err instanceof Error ? err.message : 'Network error' });
    }
  }

  const busy = state.status === 'running';

  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-card">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="text-[13px] font-black text-fg">{action.label}</h3>
          <p className="mt-1 text-[11px] text-ghost leading-relaxed">{action.caption}</p>
        </div>
        <button
          type="button"
          onClick={run}
          disabled={busy}
          className={`shrink-0 rounded-lg border px-4 py-2 text-[12px] font-black transition-colors ${
            busy
              ? 'cursor-not-allowed border-border text-ghost'
              : 'border-accent/50 bg-accent/10 text-accent hover:bg-accent/20'
          }`}
        >
          {busy ? 'Running…' : 'Run'}
        </button>
      </div>
      <StatusBadge status={state.status} message={state.message} />
    </div>
  );
}

function TokenUpdateCard() {
  const [token, setToken] = useState('');
  const [state, setState] = useState<ActionState>({ status: 'idle', message: null });

  async function submit() {
    const value = token.trim();
    if (!value || state.status === 'running') return;
    setState({ status: 'running', message: null });
    try {
      const res = await fetch('/api/v1/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: value }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        const detail = data?.detail ?? data?.message ?? `HTTP ${res.status}`;
        setState({ status: 'error', message: String(detail) });
        return;
      }
      setToken('');
      setState({ status: 'ok', message: data?.message ?? 'Token updated' });
    } catch (err) {
      setState({ status: 'error', message: err instanceof Error ? err.message : 'Network error' });
    }
  }

  const busy = state.status === 'running';

  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-card">
      <h3 className="text-[13px] font-black text-fg">Update Dhan Token</h3>
      <p className="mt-1 text-[11px] text-ghost leading-relaxed">
        Paste a new Dhan access token. LiveFeed WebSocket feeds will reconnect immediately.
      </p>
      <div className="mt-4 flex gap-3">
        <input
          type="password"
          value={token}
          onChange={e => setToken(e.target.value)}
          placeholder="Paste access token…"
          className="field h-9 min-w-0 flex-1 text-[12px]"
          disabled={busy}
          onKeyDown={e => { if (e.key === 'Enter') submit(); }}
        />
        <button
          type="button"
          onClick={submit}
          disabled={busy || !token.trim()}
          className={`shrink-0 rounded-lg border px-4 py-2 text-[12px] font-black transition-colors ${
            busy || !token.trim()
              ? 'cursor-not-allowed border-border text-ghost'
              : 'border-accent/50 bg-accent/10 text-accent hover:bg-accent/20'
          }`}
        >
          {busy ? 'Updating…' : 'Update'}
        </button>
      </div>
      <StatusBadge status={state.status} message={state.message} />
    </div>
  );
}

export function AdminPanel() {
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mx-auto max-w-2xl">
        <div className="mb-6">
          <h2 className="text-[15px] font-black text-fg">Admin</h2>
          <p className="mt-1 text-[11px] text-ghost">
            Trigger background jobs. All tasks run asynchronously — check service logs for progress.
          </p>
        </div>

        <div className="flex flex-col gap-4">
          {ACTIONS.map(action => (
            <ActionCard key={action.key} action={action} />
          ))}
          <TokenUpdateCard />
        </div>
      </div>
    </div>
  );
}
