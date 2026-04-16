'use client';

import { useCallback, useMemo, useState } from 'react';
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

export function useScreener() {
  const [rows,    setRows]    = useState<ScreenerRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [query,   setQuery]   = useState('');
  const [range,   setRange]   = useState<ScreenerRangeFilter>(DEFAULT_RANGE);
  const [presets, setPresets] = useState<Set<ScreenerPreset>>(new Set());
  const [sortCol, setSortCol] = useState('adv_20_cr');
  const [sortAsc, setSortAsc] = useState(false);

  const loadScreener = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch('/api/v1/screener');
      if (r.ok) {
        const d = await r.json();
        setRows(decorateRows(d.symbols ?? []));
      }
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

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
  }, []);

  const filteredRows = useMemo(() => {
    const filtered = applyFilters(rows, query, range, presets);
    return sortRows(filtered, sortCol, sortAsc);
  }, [rows, query, range, presets, sortCol, sortAsc]);

  return {
    rows,
    filteredRows,
    loading,
    query,   setQuery,
    range,   setRange,
    presets, togglePreset,
    sortCol, sortAsc, sortBy,
    loadScreener,
    resetFilters,
    totalCount: rows.length,
  };
}
