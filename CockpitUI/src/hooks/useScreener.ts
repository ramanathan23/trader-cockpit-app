'use client';

import { useCallback, useMemo, useRef, useState } from 'react';
import {
  DEFAULT_RANGE,
  ScreenerPreset,
  ScreenerRangeFilter,
  ScreenerRow,
  applyFilters,
  decorateRows,
  sortRows,
} from '@/domain/screener';

export type { ScreenerRangeFilter, ScreenerPreset };

const PAGE_SIZE = 2000;

export function useScreener() {
  const [rows,         setRows]         = useState<ScreenerRow[]>([]);
  const [loading,      setLoading]      = useState(false);
  const [hasMore,      setHasMore]      = useState(false);
  const [totalFromApi, setTotalFromApi] = useState(0);
  const [query,        setQuery]        = useState('');
  const [range,        setRange]        = useState<ScreenerRangeFilter>(DEFAULT_RANGE);
  const [presets,      setPresets]      = useState<Set<ScreenerPreset>>(new Set());
  const [sortCol,      setSortCol]      = useState('adv_20_cr');
  const [sortAsc,      setSortAsc]      = useState(false);
  const [fnoOnly,      setFnoOnly]      = useState(false);
  const offsetRef = useRef(0);

  const loadScreener = useCallback(async () => {
    setLoading(true);
    offsetRef.current = 0;
    try {
      const r = await fetch(`/api/v1/screener?offset=0&limit=${PAGE_SIZE}`);
      if (r.ok) {
        const d = await r.json();
        const decorated = decorateRows(d.symbols ?? []);
        const more = d.has_more ?? false;
        setRows(decorated);
        setHasMore(more);
        setTotalFromApi(d.total ?? decorated.length);
        offsetRef.current = decorated.length;
        setLoading(false);
        // Background-load remaining pages so breadth stats cover full universe
        if (more) {
          let nextMore = more;
          while (nextMore) {
            try {
              const r2 = await fetch(`/api/v1/screener?offset=${offsetRef.current}&limit=${PAGE_SIZE}`);
              if (!r2.ok) break;
              const d2 = await r2.json();
              const extra = decorateRows(d2.symbols ?? []);
              setRows(prev => [...prev, ...extra]);
              nextMore = d2.has_more ?? false;
              offsetRef.current += extra.length;
              setHasMore(nextMore);
            } catch { break; }
          }
        }
        return;
      }
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;
    setLoading(true);
    try {
      const r = await fetch(`/api/v1/screener?offset=${offsetRef.current}&limit=${PAGE_SIZE}`);
      if (r.ok) {
        const d = await r.json();
        const decorated = decorateRows(d.symbols ?? []);
        setRows(prev => [...prev, ...decorated]);
        setHasMore(d.has_more ?? false);
        offsetRef.current += decorated.length;
      }
    } catch { /* ignore */ }
    setLoading(false);
  }, [loading, hasMore]);

  const sortBy = useCallback((col: string) => {
    setSortCol(prev => {
      if (prev === col) {
        setSortAsc(a => !a);
        return prev;
      }
      setSortAsc(col === 'symbol');
      return col;
    });
  }, []);

  const togglePreset = useCallback((p: ScreenerPreset) => {
    setPresets(prev => {
      const next = new Set(prev);
      if (next.has(p)) next.delete(p); else next.add(p);
      return next;
    });
  }, []);

  const resetFilters = useCallback(() => {
    setQuery('');
    setRange(DEFAULT_RANGE);
    setPresets(new Set());
    setFnoOnly(false);
  }, []);

  const filteredRows = useMemo(() => {
    const filtered = applyFilters(rows, query, range, presets, fnoOnly);
    return sortRows(filtered, sortCol, sortAsc);
  }, [rows, query, range, presets, fnoOnly, sortCol, sortAsc]);

  return {
    rows,
    filteredRows,
    loading,
    hasMore,
    query,   setQuery,
    range,   setRange,
    presets, togglePreset,
    fnoOnly, setFnoOnly,
    sortCol, sortAsc, sortBy,
    loadScreener,
    loadMore,
    resetFilters,
    totalCount: totalFromApi || rows.length,
  };
}
