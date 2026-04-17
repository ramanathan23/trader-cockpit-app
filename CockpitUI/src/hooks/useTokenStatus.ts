'use client';

import { useEffect, useState } from 'react';

export interface TokenStatus {
  present: boolean;
  expires_at: string | null;  // ISO-8601 UTC
  expired: boolean;
}

function getLiveFeedBase(): string {
  if (typeof window === 'undefined') return 'http://localhost:8003';
  const url = new URL(window.location.origin);
  if (url.port === '3000') url.port = '8003';
  return url.toString().replace(/\/$/, '');
}

export function useTokenStatus(pollMs = 60_000) {
  const [status, setStatus] = useState<TokenStatus | null>(null);

  useEffect(() => {
    const base = (process.env.NEXT_PUBLIC_LIVE_FEED_URL ?? getLiveFeedBase()).replace(/\/$/, '');

    const fetch_ = () =>
      fetch(`${base}/api/v1/token/status`)
        .then(r => (r.ok ? r.json() : null))
        .then((d: TokenStatus | null) => { if (d) setStatus(d); })
        .catch(() => {});

    fetch_();
    const id = setInterval(fetch_, pollMs);
    return () => clearInterval(id);
  }, [pollMs]);

  return status;
}
