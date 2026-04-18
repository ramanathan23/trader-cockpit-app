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
    // Use relative path — proxied server-side by Next.js rewrite to LiveFeedService.
    // Avoids CORS issues from direct browser requests to port 8003.
    const fetch_ = () =>
      fetch('/api/v1/token/status')
        .then(r => (r.ok ? r.json() : null))
        .then((d: TokenStatus | null) => { if (d) setStatus(d); })
        .catch(() => {});

    fetch_();
    const id = setInterval(fetch_, pollMs);
    return () => clearInterval(id);
  }, [pollMs]);

  return status;
}
