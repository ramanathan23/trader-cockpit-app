'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { Signal } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { Bias, IndexName, MarketPhase, MarketStatus } from '@/domain/market';
import { alertSound } from '@/lib/audio';
import { getSignalsWebSocketUrl, LIVE_FEED } from '@/lib/api-config';

export type ConnState = 'connecting' | 'connected' | 'disconnected';

const MAX_SIGNALS         = 200;
const SIGNAL_CACHE_KEY    = 'trader-cockpit-live-signals';
const METRICS_BATCH_DELAY = 150; // ms — collect symbols then fire one POST

/** Signal types that always create a new row (never dedup). */
const ALWAYS_NEW_SIGNALS = new Set<string>();

const DEFAULT_MARKET: MarketStatus = {
  phase: '--',
  bias: { nifty: 'NEUTRAL', banknifty: 'NEUTRAL', sensex: 'NEUTRAL' },
};

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useSignals() {
  const [signals,      setSignals]      = useState<Signal[]>(() => restoreSignals());
  const [paused,       setPaused]       = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [connState,    setConnState]    = useState<ConnState>('connecting');
  const [metricsCache, setMetricsCache] = useState<Record<string, InstrumentMetrics | null>>({});
  const [marketStatus, setMarketStatus] = useState<MarketStatus>(DEFAULT_MARKET);

  // Refs allow the connection handler to always see latest state without re-subscribing.
  const pausedRef  = useRef(false);
  const pendingRef = useRef<Signal[]>([]);
  // Tracks which symbols are already fetching/fetched — prevents duplicate requests.
  const fetchingRef = useRef<Set<string>>(new Set());
  const regimeBySymbolRef = useRef<Record<string, Signal['regime']>>({});
  const issBySymbolRef = useRef<Record<string, number>>({});

  // Keep ref in sync with state
  pausedRef.current = paused;

  useEffect(() => {
    try {
      window.sessionStorage.setItem(SIGNAL_CACHE_KEY, JSON.stringify(signals.slice(0, MAX_SIGNALS)));
    } catch { /* ignore storage quota/private mode */ }
  }, [signals]);

  // ── Batch metrics fetching ─────────────────────────────────────────────────
  // Symbols are collected for METRICS_BATCH_DELAY ms, then fetched in a single
  // POST to /api/v1/instruments/metrics — eliminates N individual HTTP requests.
  const metricsPendingRef = useRef<Set<string>>(new Set());
  const metricsTimerRef   = useRef<ReturnType<typeof setTimeout> | null>(null);

  const mergeMetrics = useCallback((data: Record<string, InstrumentMetrics> | null | undefined) => {
    if (data && Object.keys(data).length > 0) {
      setMetricsCache(c => ({ ...c, ...data }));
    }
  }, []);

  const flushMetricsBatch = useCallback(() => {
    const symbols = [...metricsPendingRef.current];
    metricsPendingRef.current.clear();
    if (symbols.length === 0) return;

    fetch(LIVE_FEED.INSTRUMENTS_METRICS, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbols }),
    })
      .then(r => r.ok ? r.json() : null)
      .then((data: Record<string, InstrumentMetrics> | null) => {
        mergeMetrics(data);
      })
      .catch(() => {});
  }, [mergeMetrics]);

  const queueMetrics = useCallback((symbol: string) => {
    if (fetchingRef.current.has(symbol)) return;
    fetchingRef.current.add(symbol);
    metricsPendingRef.current.add(symbol);
    if (metricsTimerRef.current) clearTimeout(metricsTimerRef.current);
    metricsTimerRef.current = setTimeout(flushMetricsBatch, METRICS_BATCH_DELAY);
  }, [flushMetricsBatch]);

  // ── Signal ingestion — stable ref, always current ─────────────────────────

  // This ref holds the latest version of the push logic without needing
  // to be in deps of the connection useEffect (which would cause reconnects).
  const pushSignalRef = useRef<(s: Signal) => void>(null!);

  // Re-assign on every render so the closure is always fresh.
  pushSignalRef.current = (raw: Signal) => {
    let s = raw.id ? raw : { ...raw, id: `${raw.symbol}-${raw.signal_type}-${raw.timestamp}` };
    s = {
      ...s,
      regime: s.regime ?? regimeBySymbolRef.current[s.symbol],
      iss_score: s.iss_score ?? issBySymbolRef.current[s.symbol],
    };
    const isCatchup = Boolean(s._catchup);

    setSignals(prev => {
      if (isCatchup) {
        if (!ALWAYS_NEW_SIGNALS.has(s.signal_type)) {
          const key = `${s.symbol}:${s.signal_type}`;
          const idx = prev.findIndex(x => x._dedupKey === key);
          if (idx !== -1) {
            const updated = {
              ...prev[idx],
              timestamp:    s.timestamp,
              price:        s.price,
              message:      s.message,
              volume_ratio: s.volume_ratio,
              trail_stop:   s.trail_stop,
            };
            return [updated, ...prev.filter((_, i) => i !== idx)];
          }
          s = { ...s, _dedupKey: key };
        }
        if (prev.some(x => x.id === s.id)) return prev;
        s = { ...s, _count: 1, _fromCatchup: true };
        const out = [s, ...prev];
        if (out.length > MAX_SIGNALS) out.pop();
        return out;
      }

      // Live signal — dedup by symbol:type
      if (!ALWAYS_NEW_SIGNALS.has(s.signal_type)) {
        const key = `${s.symbol}:${s.signal_type}`;
        const idx = prev.findIndex(x => x._dedupKey === key);
        if (idx !== -1) {
          const ex = prev[idx];
          const updated: Signal = {
            ...ex,
            timestamp:    s.timestamp,
            price:        s.price,
            message:      s.message,
            volume_ratio: s.volume_ratio,
            trail_stop:   s.trail_stop,
            _count:       ex._fromCatchup ? ex._count : (ex._count ?? 1) + 1,
            _fromCatchup: false,
          };
          alertSound(s.signal_type);
          return [updated, ...prev.filter((_, i) => i !== idx)];
        }
        s = { ...s, _dedupKey: key };
      }

      s = { ...s, _count: 1 };
      alertSound(s.signal_type);
      const out = [s, ...prev];
      if (out.length > MAX_SIGNALS) out.pop();
      return out;
    });

    queueMetrics(s.symbol);
  };

  // ── WebSocket connection — stable effect on mount only ─────────────────────

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let destroyed = false;

    const connect = () => {
      if (destroyed) return;
      const nextSocket = new WebSocket(getSignalsWebSocketUrl());
      socket = nextSocket;

      nextSocket.onopen = () => {
        if (socket !== nextSocket) return;
        setConnState('connected');
      };

      nextSocket.onmessage = (e) => {
        try {
          if (typeof e.data !== 'string') return;
          const parsed = JSON.parse(e.data);

          // Market status envelope — update phase & bias, skip signal pipeline
          if (parsed.type === 'market_status') {
            setMarketStatus({
              phase: (parsed.session_phase ?? '--') as MarketPhase,
              bias: {
                nifty:     (parsed.index_bias?.nifty     ?? 'NEUTRAL') as Bias,
                banknifty: (parsed.index_bias?.banknifty ?? 'NEUTRAL') as Bias,
                sensex:    (parsed.index_bias?.sensex    ?? 'NEUTRAL') as Bias,
              } as Record<IndexName, Bias>,
            });
            return;
          }

          if (parsed.type === 'regime_update') {
            regimeBySymbolRef.current[parsed.symbol] = parsed.regime;
            setSignals(prev => prev.map(s => s.symbol === parsed.symbol ? { ...s, regime: parsed.regime } : s));
            return;
          }

          if (parsed.type === 'session_prediction') {
            if (parsed.iss_score != null) issBySymbolRef.current[parsed.symbol] = Number(parsed.iss_score);
            setSignals(prev => prev.map(s => s.symbol === parsed.symbol ? { ...s, iss_score: parsed.iss_score } : s));
            return;
          }

          const s: Signal = parsed;
          if (pausedRef.current) {
            pendingRef.current.push(s);
            setPendingCount(pendingRef.current.length);
          } else {
            pushSignalRef.current(s);
          }
        } catch { /* ignore malformed JSON */ }
      };

      nextSocket.onerror = () => {
        if (socket === nextSocket) {
          nextSocket.close();
        }
      };

      nextSocket.onclose = () => {
        if (socket !== nextSocket || destroyed) return;
        setConnState('disconnected');
        socket = null;
        retryTimer = setTimeout(() => {
          setConnState('connecting');
          connect();
        }, 3000);
      };
    };

    connect();
    return () => {
      destroyed = true;
      socket?.close();
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, []); // intentionally empty — socket lifecycle is independent of React state

  // ── Controls ───────────────────────────────────────────────────────────────

  const togglePause = useCallback(() => {
    setPaused(p => {
      if (p) {
        // Flush pending queue on resume
        const pending = [...pendingRef.current];
        pendingRef.current = [];
        setPendingCount(0);
        pending.forEach(s => pushSignalRef.current(s));
      }
      return !p;
    });
  }, []);

  const clearSignals = useCallback(() => {
    setSignals([]);
    pendingRef.current = [];
    setPendingCount(0);
    try { window.sessionStorage.removeItem(SIGNAL_CACHE_KEY); } catch {}
  }, []);

  return {
    signals,
    paused,
    pendingCount,
    connState,
    metricsCache,
    marketStatus,
    mergeMetrics,
    togglePause,
    clearSignals,
  };
}

function restoreSignals(): Signal[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.sessionStorage.getItem(SIGNAL_CACHE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.slice(0, MAX_SIGNALS).map((signal: Signal) => ({
      ...signal,
      _count: signal._count ?? 1,
      _fromCatchup: signal._fromCatchup ?? true,
    }));
  } catch {
    return [];
  }
}
