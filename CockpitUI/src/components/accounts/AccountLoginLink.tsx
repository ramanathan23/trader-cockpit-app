'use client';

import { ExternalLink } from 'lucide-react';
import type { ZerodhaAccountStatus } from '@/components/admin/adminTypes';
import { statusClass } from './accountFmt';

export function needsLogin(account?: ZerodhaAccountStatus | null) {
  if (!account?.has_credentials) return false;
  return account.status !== 'connected';
}

export function AccountLoginLink({
  account,
  showUrl = false,
}: {
  account?: ZerodhaAccountStatus | null;
  showUrl?: boolean;
}) {
  if (!account?.has_credentials || !account.login_url) return null;
  const loginNeeded = needsLogin(account);
  if (!loginNeeded && !showUrl) return null;

  return (
    <div className="mt-2 rounded border border-amber/30 bg-amber/10 px-2 py-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className={`rounded-full border px-2 py-0.5 text-[10px] font-black ${statusClass(account.status)}`}>
          {account.status.replace('_', ' ')}
        </span>
        <a
          href={account.login_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 rounded border border-accent/40 bg-accent/10 px-2 py-1 text-[11px] font-black text-accent hover:bg-accent/20"
        >
          Login <ExternalLink size={12} />
        </a>
      </div>
      {(showUrl || loginNeeded) && (
        <div className="mt-2 break-all rounded bg-base/70 px-2 py-1 font-mono text-[10px] text-dim">
          {account.login_url}
        </div>
      )}
      {account.expires_at && (
        <div className="mt-1 text-[10px] text-ghost">Expires {account.expires_at.slice(0, 16).replace('T', ' ')}</div>
      )}
      {account.last_error && <div className="mt-1 text-[10px] text-bear">{account.last_error}</div>}
    </div>
  );
}
