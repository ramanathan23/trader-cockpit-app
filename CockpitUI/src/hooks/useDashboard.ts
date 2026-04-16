'use client';

import { useCallback, useRef, useState } from 'react';
import type { DashboardResponse, DashboardStats, ScoredSymbol } from '@/domain/dashboard';

const EMPTY_STATS: DashboardStats = {
  total_scored: 0, watchlist_count: 0, avg_score: 0, max_score: 0,
  min_score: 0, high_conviction: 0, above_average: 0, score_date: '', computed_at: '',
};

const PAGE_SIZE = 50;

export function useDashboard() {
  const [stats,   setStats]   = useState<DashboardStats>(EMPTY_STATS);
  const [scores,  setScores]  = useState<ScoredSymbol[]>([]);
  const [loading, setLoading] = useState(false);
  const [computing, setComputing] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const fetched = useRef(false);
  const offsetRef = useRef(0);

  const loadDashboard = useCallback(async (opts?: { watchlistOnly?: boolean; date?: string; segment?: string }) => {
    setLoading(true);
    offsetRef.current = 0;
    try {
      const params = new URLSearchParams();
      if (opts?.watchlistOnly) params.set('watchlist_only', 'true');
      if (opts?.date) params.set('score_date', opts.date);
      if (opts?.segment) params.set('segment', opts.segment);
      params.set('limit', String(PAGE_SIZE));
      params.set('offset', '0');

      const res = await fetch(`/scorer/dashboard?${params}`);
      if (!res.ok) throw new Error(`Dashboard fetch failed: ${res.status}`);
      const data: DashboardResponse = await res.json();
      setStats(data.stats);
      setScores(data.scores);
      setHasMore(data.has_more);
      offsetRef.current = data.scores.length;
      fetched.current = true;
    } catch (err) {
      console.error('[useDashboard]', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMore = useCallback(async (opts?: { watchlistOnly?: boolean; date?: string; segment?: string }) => {
    if (loading || !hasMore) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (opts?.watchlistOnly) params.set('watchlist_only', 'true');
      if (opts?.date) params.set('score_date', opts.date);
      if (opts?.segment) params.set('segment', opts.segment);
      params.set('limit', String(PAGE_SIZE));
      params.set('offset', String(offsetRef.current));
      params.set('balanced', 'false');

      const res = await fetch(`/scorer/dashboard?${params}`);
      if (!res.ok) throw new Error(`Dashboard loadMore failed: ${res.status}`);
      const data: DashboardResponse = await res.json();
      setScores(prev => [...prev, ...data.scores]);
      setHasMore(data.has_more);
      offsetRef.current += data.scores.length;
    } catch (err) {
      console.error('[useDashboard] loadMore', err);
    } finally {
      setLoading(false);
    }
  }, [loading, hasMore]);

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
    stats, scores, loading, computing, hasMore, fetched: fetched.current,
    loadDashboard, loadMore, triggerCompute,
  };
}
