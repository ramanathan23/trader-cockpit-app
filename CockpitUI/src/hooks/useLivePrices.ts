'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { LIVE_FEED } from '@/lib/api-config';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { LivePriceData } from '@/components/ui/LivePrice';

interface PriceEvent {
  type?: string;
  symbol?: string;
  current_price?: number;
}

export function useLivePrices(
  symbols: string[],
  enabled: boolean,
): Record<string, LivePriceData> {
  const [prices, setPrices] = useState<Record<string, LivePriceData>>({});
  const symbolsRef = useRef<string[]>(symbols);
  const symbolSetRef = useRef<Set<string>>(new Set(symbols));
  symbolsRef.current = symbols;
  symbolSetRef.current = new Set(symbols);
  const symbolsKey = useMemo(() => symbols.join('|'), [symbols]);

  useEffect(() => {
    if (!enabled) return;

    let active = true;
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
            ltp:       m.current_price ?? m.day_close ?? null,
            prevClose: m.prev_day_close ?? null,
          };
        }
        setPrices(map);
      })
      .catch(() => {});

    const events = new EventSource(LIVE_FEED.PRICES_STREAM);
    events.onmessage = event => {
      if (!active) return;
      try {
        const data = JSON.parse(event.data) as PriceEvent;
        if (data.type !== 'price' || !data.symbol || data.current_price == null) return;
        if (!symbolSetRef.current.has(data.symbol)) return;
        setPrices(prev => ({
          ...prev,
          [data.symbol!]: {
            ltp:       data.current_price ?? null,
            prevClose: prev[data.symbol!]?.prevClose ?? null,
          },
        }));
      } catch { /* ignore malformed SSE payloads */ }
    };

    return () => {
      active = false;
      events.close();
    };
  }, [enabled, symbolsKey]);

  return prices;
}
