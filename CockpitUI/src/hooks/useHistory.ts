'use client';

import { useCallback, useEffect, useState } from 'react';
import type { Signal } from '@/domain/signal';
import { todayIST } from '@/lib/fmt';

interface HistoryState {
  signals: Signal[];
  availableDates: string[];
  loading: boolean;
  date: string;
}

export function useHistory() {
  const [state, setState] = useState<HistoryState>({
    signals:        [],
    availableDates: [],
    loading:        false,
    date:           todayIST(),
  });

  const loadDates = useCallback(async () => {
    try {
      const r = await fetch('/api/v1/signals/history/dates');
      if (r.ok) {
        const d = await r.json();
        setState(s => ({ ...s, availableDates: d.dates ?? [] }));
      }
    } catch { /* ignore */ }
  }, []);

  const loadHistory = useCallback(async (date: string) => {
    setState(s => ({ ...s, loading: true, signals: [], date }));
    try {
      const r = await fetch(`/api/v1/signals/history?date=${date}`);
      if (r.ok) {
        const d = await r.json();
        const newestFirst = [...(d.signals ?? [])].reverse();
        setState(s => ({
          ...s,
          loading:        false,
          signals:        newestFirst,
          availableDates: d.available_dates ?? s.availableDates,
        }));
      } else {
        setState(s => ({ ...s, loading: false }));
      }
    } catch {
      setState(s => ({ ...s, loading: false }));
    }
  }, []);

  useEffect(() => {
    loadDates();
  }, [loadDates]);

  return {
    ...state,
    loadHistory,
    reload: () => loadHistory(state.date),
  };
}
