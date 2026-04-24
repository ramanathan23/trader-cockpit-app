import type { TokenStatus } from '@/hooks/useTokenStatus';

/** Human-readable phase descriptions shown as tooltip on the phase chip. */
export const PHASE_TITLES: Record<string, string> = {
  DRIVE_WINDOW:    '9:15-9:45. High-momentum open; trend entries need fast confirmation.',
  EXECUTION:       '9:45-11:30. Primary execution window; signals have better context.',
  DEAD_ZONE:       '11:30-14:30. Lower conviction, more chop, stricter selection.',
  CLOSE_MOMENTUM:  '14:30-15:15. Late directional flow can resume.',
  SESSION_END:     '15:15-15:30. Avoid fresh risk unless already planned.',
  '--':            'Market closed or phase unavailable.',
};

export interface TokenMeta { label: string; color: string; title: string; }

/** Derive display label, color, and tooltip from the token status object. */
export function tokenMeta(tokenStatus?: TokenStatus | null): TokenMeta {
  if (!tokenStatus)
    return { label: 'Token unknown', color: 'rgb(var(--ghost))', title: 'Dhan token status unavailable' };

  if (!tokenStatus.present)
    return { label: 'No token', color: 'rgb(var(--bear))', title: 'Dhan access token is not set' };

  if (tokenStatus.expired) {
    return {
      label: 'Token expired',
      color: 'rgb(var(--bear))',
      title: tokenStatus.expires_at ? `Expired at ${new Date(tokenStatus.expires_at).toLocaleString()}` : 'Token expired',
    };
  }

  if (!tokenStatus.expires_at)
    return { label: 'Token ok', color: 'rgb(var(--bull))', title: 'Token present; expiry unavailable' };

  const expires = new Date(tokenStatus.expires_at);
  const ms      = expires.getTime() - Date.now();
  const minutes = Math.max(0, Math.floor(ms / 60_000));
  const hours   = Math.floor(minutes / 60);
  const days    = Math.floor(hours / 24);

  if (hours < 1)  return { label: `Token ${minutes}m`, color: 'rgb(var(--amber))', title: `Expires ${expires.toLocaleString()}` };
  if (hours < 24) return { label: `Token ${hours}h`,   color: 'rgb(var(--bull))',  title: `Expires ${expires.toLocaleString()}` };
  return             { label: `Token ${days}d`,         color: 'rgb(var(--bull))',  title: `Expires ${expires.toLocaleString()}` };
}
