'use client';

import { useEffect, useState } from 'react';
import { LIVE_FEED } from '@/lib/api-config';

export interface TokenStatus {
  present: boolean;
  expires_at: string | null;  // ISO-8601 UTC
  expired: boolean;
}

export function useTokenStatus(pollMs = 60_000) {
  const [status, setStatus] = useState<TokenStatus | null>(null);

  useEffect(() => {
    const fetch_ = () =>
      fetch(LIVE_FEED.TOKEN_STATUS)
        .then(r => (r.ok ? r.json() : null))
        .then((d: TokenStatus | null) => { if (d) setStatus(d); })
        .catch(() => {});

    fetch_();
    const id = setInterval(fetch_, pollMs);
    return () => clearInterval(id);
  }, [pollMs]);

  return status;
}
