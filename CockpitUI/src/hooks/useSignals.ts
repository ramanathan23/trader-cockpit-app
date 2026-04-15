'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { InstrumentMetrics, Signal } from '@/domain/signal';
import { alertSound } from '@/lib/audio';

export type ConnState = 'connecting' | 'connected' | 'disconnected';

const MAX_SIGNALS         = 200;
const METRICS_CONCURRENCY = 6;   // max parallel metrics HTTP requests
const ALWAYS_NEW    = new Set(['OPEN_DRIVE_ENTRY', 'DRIVE_FAILED', 'EXIT']);
const ALWAYS_NEW_CU = new Set(['OPEN_DRIVE_ENTRY', 'DRIVE_FAILED', 'EXIT']);

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useSignals() {
  const [signals,      setSignals]      = useState<Signal[]>([]);
  const [paused,       setPaused]       = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [connState,    setConnState]    = useState<ConnState>('connecting');
  const [metricsCache, setMetricsCache] = useState<Record<string, InstrumentMetrics | null>>({});

  // Refs allow SSE handler to always see latest state without re-subscribing.
  const pausedRef  = useRef(false);
  const pendingRef = useRef<Signal[]>([]);
  // Tracks which symbols are already fetching/fetched — prevents duplicate requests.
  const fetchingRef = useRef<Set<string>>(new Set());

  // Keep ref in sync with state
  pausedRef.current = paused;

  // ── Batch metrics fetching ─────────────────────────────────────────────────
  // Max METRICS_CONCURRENCY parallel requests. Results accumulate in metricsAccRef
  // and flush into a single setMetricsCache after an 80ms debounce — prevents the
  // render storm (was: 2 setState calls per symbol → N×2 re-renders on catchup).
  const metricsQueueRef  = useRef<string[]>([]);
  const metricsActiveRef = useRef(0);
  const metricsAccRef    = useRef<Record<string, InstrumentMetrics>>({});
  const metricsTimerRef  = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Held in a ref so the drain loop can recurse without stale closures or useCallback deps.
  const drainMetricsRef = useRef<() => void>(null!);
  drainMetricsRef.current = () => {
    while (metricsActiveRef.current < METRICS_CONCURRENCY && metricsQueueRef.current.length > 0) {
      const sym = metricsQueueRef.current.shift()!;
      metricsActiveRef.current++;
      fetch(`/api/v1/instrument/${encodeURIComponent(sym)}/metrics`)
        .then(r => r.ok ? r.json() : null)
        .then((data: InstrumentMetrics | null) => {
          if (data) metricsAccRef.current[sym] = data;
          metricsActiveRef.current--;
          // Debounce: collect concurrent completions into one setState
          if (metricsTimerRef.current) clearTimeout(metricsTimerRef.current);
          metricsTimerRef.current = setTimeout(() => {
            const upd = metricsAccRef.current;
            metricsAccRef.current = {};
            if (Object.keys(upd).length > 0) setMetricsCache(c => ({ ...c, ...upd }));
          }, 80);
          drainMetricsRef.current();
        })
        .catch(() => { metricsActiveRef.current--; drainMetricsRef.current(); });
    }
  };

  const queueMetrics = (symbol: string) => {
    if (fetchingRef.current.has(symbol)) return;
    fetchingRef.current.add(symbol);
    metricsQueueRef.current.push(symbol);
    drainMetricsRef.current();
  };

  // ── Signal ingestion — stable ref, always current ─────────────────────────

  // This ref holds the latest version of the push logic without needing
  // to be in deps of the SSE useEffect (which would cause reconnects).
  const pushSignalRef = useRef<(s: Signal) => void>(null!);

  // Re-assign on every render so the closure is always fresh.
  pushSignalRef.current = (raw: Signal) => {
    let s = raw.id ? raw : { ...raw, id: `${raw.symbol}-${raw.signal_type}-${raw.timestamp}` };
    const isCatchup = Boolean(s._catchup);

    setSignals(prev => {
      if (isCatchup) {
        if (!ALWAYS_NEW_CU.has(s.signal_type)) {
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
      if (!ALWAYS_NEW.has(s.signal_type)) {
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

  // ── SSE connection — stable effect on mount only ───────────────────────────

  useEffect(() => {
    let src: EventSource | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let destroyed = false;

    const connect = () => {
      if (destroyed) return;
      src = new EventSource('/api/v1/signals/stream');

      src.onopen = () => setConnState('connected');

      src.onmessage = (e) => {
        try {
          const s: Signal = JSON.parse(e.data);
          if (pausedRef.current) {
            pendingRef.current.push(s);
            setPendingCount(pendingRef.current.length);
          } else {
            pushSignalRef.current(s);
          }
        } catch { /* ignore malformed JSON */ }
      };

      src.onerror = () => {
        setConnState('disconnected');
        src?.close();
        src = null;
        retryTimer = setTimeout(() => {
          setConnState('connecting');
          connect();
        }, 3000);
      };
    };

    connect();
    return () => {
      destroyed = true;
      src?.close();
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, []); // intentionally empty — SSE lifecycle is independent of React state

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
  }, []);

  return {
    signals,
    paused,
    pendingCount,
    connState,
    metricsCache,
    togglePause,
    clearSignals,
  };
}
