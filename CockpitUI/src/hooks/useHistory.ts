'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { Signal } from '@/domain/signal';
import { todayIST } from '@/lib/fmt';
import { LIVE_FEED } from '@/lib/api-config';

const PAGE_SIZE = 100;

interface HistoryState {
  signals: Signal[];
  availableDates: string[];
  loading: boolean;
  date: string;
  hasMore: boolean;
}

export function useHistory() {
  const [state, setState] = useState<HistoryState>({
    signals:        [],
    availableDates: [],
    loading:        false,
    date:           todayIST(),
    hasMore:        false,
  });
  const offsetRef = useRef(0);

  const loadDates = useCallback(async () => {
    try {
      const r = await fetch(LIVE_FEED.SIGNAL_HISTORY_DATES);
      if (r.ok) {
        const d = await r.json();
        setState(s => ({ ...s, availableDates: d.dates ?? [] }));
      }
    } catch { /* ignore */ }
  }, []);

  const loadHistory = useCallback(async (date: string) => {
    setState(s => ({ ...s, loading: true, signals: [], date, hasMore: false }));
    offsetRef.current = 0;
    try {
      const r = await fetch(`${LIVE_FEED.SIGNAL_HISTORY}?date=${date}&offset=0&limit=${PAGE_SIZE}`);
      if (r.ok) {
        const d = await r.json();
        const newestFirst = [...(d.signals ?? [])].reverse();
        offsetRef.current = newestFirst.length;
        setState(s => ({
          ...s,
          loading:        false,
          signals:        newestFirst,
          availableDates: d.available_dates ?? s.availableDates,
          hasMore:        d.has_more ?? false,
        }));
      } else {
        setState(s => ({ ...s, loading: false }));
      }
    } catch {
      setState(s => ({ ...s, loading: false }));
    }
  }, []);

  const loadMore = useCallback(async () => {
    if (state.loading || !state.hasMore) return;
    setState(s => ({ ...s, loading: true }));
    try {
      const r = await fetch(`${LIVE_FEED.SIGNAL_HISTORY}?date=${state.date}&offset=${offsetRef.current}&limit=${PAGE_SIZE}`);
      if (r.ok) {
        const d = await r.json();
        const newestFirst = [...(d.signals ?? [])].reverse();
        offsetRef.current += newestFirst.length;
        setState(s => ({
          ...s,
          loading: false,
          signals: [...s.signals, ...newestFirst],
          hasMore: d.has_more ?? false,
        }));
      } else {
        setState(s => ({ ...s, loading: false }));
      }
    } catch {
      setState(s => ({ ...s, loading: false }));
    }
  }, [state.loading, state.hasMore, state.date]);

  useEffect(() => {
    loadDates();
  }, [loadDates]);

  return {
    ...state,
    loadHistory,
    loadMore,
    reload: () => loadHistory(state.date),
  };
}
