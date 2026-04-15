'use client';

import { useCallback, useEffect, useState } from 'react';
import type { Bias, IndexName, MarketPhase, MarketStatus } from '@/domain/market';

const DEFAULT: MarketStatus = {
  phase: '--',
  bias: { nifty: 'NEUTRAL', banknifty: 'NEUTRAL', sensex: 'NEUTRAL' },
};

export function useMarketStatus() {
  const [status, setStatus] = useState<MarketStatus>(DEFAULT);
  const [clock, setClock] = useState('--:--:--');

  const poll = useCallback(async () => {
    try {
      const r = await fetch('/api/v1/status');
      if (!r.ok) return;
      const d = await r.json();
      setStatus({
        phase: (d.session_phase ?? '--') as MarketPhase,
        bias: {
          nifty:     (d.index_bias?.nifty     ?? 'NEUTRAL') as Bias,
          banknifty: (d.index_bias?.banknifty ?? 'NEUTRAL') as Bias,
          sensex:    (d.index_bias?.sensex    ?? 'NEUTRAL') as Bias,
        } as Record<IndexName, Bias>,
      });
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    poll();
    const id = setInterval(poll, 10_000);
    return () => clearInterval(id);
  }, [poll]);

  useEffect(() => {
    const tick = () => {
      const ist = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
      setClock(ist.toTimeString().slice(0, 8));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return { ...status, clock };
}
