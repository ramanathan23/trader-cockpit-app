'use client';

import { useCallback, useRef, useState } from 'react';
import type { DashboardResponse, DashboardStats, ScoredSymbol } from '@/domain/dashboard';

const EMPTY_STATS: DashboardStats = {
  total_scored: 0, watchlist_count: 0, avg_score: 0, max_score: 0,
  min_score: 0, high_conviction: 0, above_average: 0, score_date: '', computed_at: '',
};

export function useDashboard() {
  const [stats,   setStats]   = useState<DashboardStats>(EMPTY_STATS);
  const [scores,  setScores]  = useState<ScoredSymbol[]>([]);
  const [loading, setLoading] = useState(false);
  const [computing, setComputing] = useState(false);
  const fetched = useRef(false);

  const loadDashboard = useCallback(async (opts?: { watchlistOnly?: boolean; date?: string }) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (opts?.watchlistOnly) params.set('watchlist_only', 'true');
      if (opts?.date) params.set('score_date', opts.date);
      params.set('limit', '1000');

      const res = await fetch(`/scorer/dashboard?${params}`);
      if (!res.ok) throw new Error(`Dashboard fetch failed: ${res.status}`);
      const data: DashboardResponse = await res.json();
      setStats(data.stats);
      setScores(data.scores);
      fetched.current = true;
    } catch (err) {
      console.error('[useDashboard]', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const triggerCompute = useCallback(async () => {
    setComputing(true);
    try {
      const res = await fetch('/scorer/scores/compute', { method: 'POST' });
      if (!res.ok) throw new Error(`Compute trigger failed: ${res.status}`);
    } catch (err) {
      console.error('[useDashboard] compute trigger', err);
    } finally {
      setComputing(false);
    }
  }, []);

  return {
    stats, scores, loading, computing, fetched: fetched.current,
    loadDashboard, triggerCompute,
  };
}
