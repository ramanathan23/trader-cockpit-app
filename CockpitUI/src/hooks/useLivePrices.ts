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

const sharedPrices: Record<string, LivePriceData> = {};
const priceListeners = new Set<(symbol: string, price: LivePriceData) => void>();
let sharedEvents: EventSource | null = null;

function ensurePriceStream() {
  if (sharedEvents || typeof window === 'undefined') return;
  sharedEvents = new EventSource(LIVE_FEED.PRICES_STREAM);
  sharedEvents.onmessage = event => {
    try {
      const data = JSON.parse(event.data) as PriceEvent;
      if (data.type !== 'price' || !data.symbol || data.current_price == null) return;
      const next = {
        ltp: data.current_price,
        prevClose: sharedPrices[data.symbol]?.prevClose ?? null,
      };
      sharedPrices[data.symbol] = next;
      priceListeners.forEach(listener => listener(data.symbol!, next));
    } catch { /* ignore malformed SSE payloads */ }
  };
  sharedEvents.onerror = () => {
    sharedEvents?.close();
    sharedEvents = null;
    window.setTimeout(ensurePriceStream, 3000);
  };
}

function pickPrices(symbols: string[]): Record<string, LivePriceData> {
  const out: Record<string, LivePriceData> = {};
  for (const symbol of symbols) {
    if (sharedPrices[symbol]) out[symbol] = sharedPrices[symbol];
  }
  return out;
}

function mergeMetricPrice(symbol: string, metricPrice: LivePriceData): LivePriceData {
  const current = sharedPrices[symbol];
  const next = {
    ltp: current?.ltp ?? metricPrice.ltp,
    prevClose: metricPrice.prevClose ?? current?.prevClose ?? null,
  };
  sharedPrices[symbol] = next;
  return next;
}

export function useLivePrices(
  symbols: string[],
  enabled: boolean,
): Record<string, LivePriceData> {
  const [prices, setPrices] = useState<Record<string, LivePriceData>>(() => pickPrices(symbols));
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

    setPrices(pickPrices(syms));
    ensurePriceStream();

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
          map[sym] = mergeMetricPrice(sym, {
            ltp:       m.current_price ?? m.day_close ?? null,
            prevClose: m.prev_day_close ?? null,
          });
        }
        setPrices(prev => ({ ...prev, ...map }));
      })
      .catch(() => {});

    const listener = (symbol: string, price: LivePriceData) => {
      if (!active) return;
      if (!symbolSetRef.current.has(symbol)) return;
      setPrices(prev => ({ ...prev, [symbol]: price }));
    };
    priceListeners.add(listener);

    return () => {
      active = false;
      priceListeners.delete(listener);
    };
  }, [enabled, symbolsKey]);

  return prices;
}
