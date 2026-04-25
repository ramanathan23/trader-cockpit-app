'use client';

import { useCallback, useDeferredValue, useMemo, useRef, useState } from 'react';
import {
  applyFilters, DEFAULT_RANGE, decorateRows,
  type ScreenerPreset, type ScreenerRangeFilter,
} from '@/domain/screener';
import type { ScoredSymbol } from '@/domain/dashboard';
import { mergeStockRows, sortStockRows, type StockRow } from '@/domain/stocklist';

const PAGE_SIZE = 500;

export function useStockList(noteEntries?: Record<string, { text: string }[]>) {
  const [rows,    setRows]    = useState<StockRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [totalFromApi, setTotalFromApi] = useState(0);
  const [query,   setQuery]   = useState('');
  const [range,   setRange]   = useState<ScreenerRangeFilter>(DEFAULT_RANGE);
  const [presets, setPresets] = useState<Set<ScreenerPreset>>(new Set());
  const [fnoOnly, setFnoOnly] = useState(false);
  const [sortCol, setSortCol] = useState('rank');
  const [sortAsc, setSortAsc] = useState(true);
  const fetched = useRef(false);
  const offsetRef = useRef(0);
  const scoreRowsRef = useRef<ScoredSymbol[]>([]);
  const deferredQuery = useDeferredValue(query);

  const load = useCallback(async () => {
    setLoading(true);
    offsetRef.current = 0;
    try {
      const [sr, dr] = await Promise.allSettled([
        fetch(`/api/v1/screener?offset=0&limit=${PAGE_SIZE}`).then(r => r.ok ? r.json() : { symbols: [] }),
        fetch(`/scorer/dashboard?limit=1000&_ts=${Date.now()}`).then(r => r.ok ? r.json() : { scores: [] }),
      ]);
      const screenerData = sr.status === 'fulfilled' ? sr.value : { symbols: [] };
      const dashData     = dr.status === 'fulfilled' ? dr.value : { scores: [] };
      const decorated    = decorateRows(screenerData.symbols ?? []);
      scoreRowsRef.current = dashData.scores ?? [];
      setRows(mergeStockRows(decorated, scoreRowsRef.current));
      setHasMore(screenerData.has_more ?? false);
      setTotalFromApi(screenerData.total ?? decorated.length);
      offsetRef.current = decorated.length;
    } catch { /* ignore */ }
    setLoading(false);
    fetched.current = true;
  }, []);

  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;
    setLoading(true);
    try {
      const r = await fetch(`/api/v1/screener?offset=${offsetRef.current}&limit=${PAGE_SIZE}`);
      if (r.ok) {
        const d = await r.json();
        const decorated = decorateRows(d.symbols ?? []);
        const merged = mergeStockRows(decorated, scoreRowsRef.current);
        setRows(prev => [...prev, ...merged]);
        setHasMore(d.has_more ?? false);
        setTotalFromApi(d.total ?? offsetRef.current + decorated.length);
        offsetRef.current += decorated.length;
      }
    } catch { /* ignore */ }
    setLoading(false);
  }, [loading, hasMore]);

  const sortBy = useCallback((col: string) => {
    setSortCol(prev => {
      if (prev === col) { setSortAsc(a => !a); return prev; }
      setSortAsc(col === 'symbol');
      return col;
    });
  }, []);

  const togglePreset = useCallback((p: ScreenerPreset) => {
    setPresets(prev => { const n = new Set(prev); n.has(p) ? n.delete(p) : n.add(p); return n; });
  }, []);

  const resetFilters = useCallback(() => {
    setQuery(''); setRange(DEFAULT_RANGE); setPresets(new Set()); setFnoOnly(false);
  }, []);

  const notesText = useMemo(() => {
    if (!noteEntries) return undefined;
    const r: Record<string, string> = {};
    for (const [sym, entries] of Object.entries(noteEntries)) {
      if (entries.length > 0) r[sym] = entries.map(e => e.text).join(' ');
    }
    return r;
  }, [noteEntries]);

  const filteredRows = useMemo(() => {
    const filtered = applyFilters(rows, deferredQuery, range, presets, fnoOnly, notesText);
    return sortStockRows(filtered, sortCol, sortAsc);
  }, [rows, deferredQuery, range, presets, fnoOnly, notesText, sortCol, sortAsc]);

  return {
    rows, filteredRows, loading,
    query, setQuery, range, setRange,
    presets, togglePreset, fnoOnly, setFnoOnly,
    sortCol, sortAsc, sortBy, load, loadMore, resetFilters,
    fetched: fetched.current,
    hasMore,
    totalCount: totalFromApi || rows.length,
  };
}
