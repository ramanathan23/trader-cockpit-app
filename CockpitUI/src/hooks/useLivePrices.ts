'use client';

import { useEffect, useRef, useState } from 'react';
import { LIVE_FEED } from '@/lib/api-config';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { LivePriceData } from '@/components/ui/LivePrice';

const POLL_MS = 12_000;

export function useLivePrices(
  symbols: string[],
  enabled: boolean,
): Record<string, LivePriceData> {
  const [prices, setPrices] = useState<Record<string, LivePriceData>>({});
  const symbolsRef = useRef<string[]>(symbols);
  symbolsRef.current = symbols;

  useEffect(() => {
    if (!enabled) return;

    let active = true;

    const poll = () => {
      const syms = symbolsRef.current;
      if (syms.length === 0) return;
      fetch(LIVE_FEED.INSTRUMENTS_METRICS, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ symbols: syms }),
      })
        .then(r => r.ok ? r.json() : null)
        .then((data: Record<string, InstrumentMetrics> | null) => {
          if (!active || !data) return;
          const map: Record<string, LivePriceData> = {};
          for (const [sym, m] of Object.entries(data)) {
            map[sym] = {
              ltp:      m.current_price ?? m.day_close ?? null,
              prevClose: m.prev_day_close ?? null,
            };
          }
          setPrices(map);
        })
        .catch(() => {});
    };

    poll();
    const id = setInterval(poll, POLL_MS);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [enabled]); // symbolsRef tracks latest symbols without restarting interval

  return prices;
}
