'use client';

import { useCallback, useMemo, useRef, useState } from 'react';
import {
  applyFilters, DEFAULT_RANGE, decorateRows,
  type ScreenerPreset, type ScreenerRangeFilter,
} from '@/domain/screener';
import { mergeStockRows, sortStockRows, type StockRow } from '@/domain/stocklist';

export function useStockList(noteEntries?: Record<string, { text: string }[]>) {
  const [rows,    setRows]    = useState<StockRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [query,   setQuery]   = useState('');
  const [range,   setRange]   = useState<ScreenerRangeFilter>(DEFAULT_RANGE);
  const [presets, setPresets] = useState<Set<ScreenerPreset>>(new Set());
  const [fnoOnly, setFnoOnly] = useState(false);
  const [sortCol, setSortCol] = useState('rank');
  const [sortAsc, setSortAsc] = useState(true);
  const fetched = useRef(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [sr, dr] = await Promise.allSettled([
        fetch('/api/v1/screener?offset=0&limit=2000').then(r => r.ok ? r.json() : { symbols: [] }),
        fetch(`/scorer/dashboard?limit=1000&_ts=${Date.now()}`).then(r => r.ok ? r.json() : { scores: [] }),
      ]);
      const screenerData = sr.status === 'fulfilled' ? sr.value : { symbols: [] };
      const dashData     = dr.status === 'fulfilled' ? dr.value : { scores: [] };
      const decorated    = decorateRows(screenerData.symbols ?? []);
      setRows(mergeStockRows(decorated, dashData.scores ?? []));
    } catch { /* ignore */ }
    setLoading(false);
    fetched.current = true;
  }, []);

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
    const filtered = applyFilters(rows, query, range, presets, fnoOnly, notesText);
    return sortStockRows(filtered, sortCol, sortAsc);
  }, [rows, query, range, presets, fnoOnly, notesText, sortCol, sortAsc]);

  return {
    rows, filteredRows, loading,
    query, setQuery, range, setRange,
    presets, togglePreset, fnoOnly, setFnoOnly,
    sortCol, sortAsc, sortBy, load, resetFilters,
    fetched: fetched.current,
    totalCount: rows.length,
  };
}
