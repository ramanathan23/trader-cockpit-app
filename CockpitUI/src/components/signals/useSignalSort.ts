'use client';

import { useCallback, useMemo, useState } from 'react';
import { filterSignals, type Signal, type SignalCategory, type SignalType } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';

export type SignalSortKey = 'timestamp' | 'price' | 'volume_ratio' | 'score' | 'adv' | 'chg_pct' | 'f52h_pct';

export const TABLE_HEADERS: { h: string; title: string; align?: 'right' | 'center'; sortKey?: SignalSortKey }[] = [
  { h: 'TIME',  title: 'Signal trigger time',              sortKey: 'timestamp' },
  { h: 'SYMBOL',title: 'Symbol and direction' },
  { h: 'TYPE',  title: 'Signal type' },
  { h: 'PRICE', title: 'Trigger price',                    align: 'right', sortKey: 'price' },
  { h: 'VOL',   title: 'Volume ratio versus average',      align: 'right', sortKey: 'volume_ratio' },
  { h: 'MTF',   title: '15m and 1h bias' },
  { h: 'LEVELS',title: 'Entry, stop loss and target' },
  { h: 'ADV',   title: 'Average daily traded value',       align: 'right', sortKey: 'adv' },
  { h: 'CHG%',  title: 'Change versus previous close',     align: 'right', sortKey: 'chg_pct' },
  { h: '52H%',  title: 'Distance from 52-week high',       align: 'right', sortKey: 'f52h_pct' },
  { h: 'SCORE', title: 'Composite score',                  align: 'right', sortKey: 'score' },
  { h: 'NOTE',  title: 'Private trading note' },
];

interface UseSignalSortProps {
  signals: Signal[];
  category: SignalCategory;
  minAdvCr: number;
  metricsCache: Record<string, InstrumentMetrics | null>;
  subType?: SignalType | null;
  fnoOnly?: boolean;
}

export function useSignalSort({ signals, category, minAdvCr, metricsCache, subType, fnoOnly }: UseSignalSortProps) {
  const [query,   setQuery]   = useState('');
  const [sortKey, setSortKey] = useState<SignalSortKey | null>(null);
  const [sortAsc, setSortAsc] = useState(false);

  const handleSort  = useCallback((key: SignalSortKey) => {
    setSortAsc(prev => sortKey === key ? !prev : key === 'timestamp');
    setSortKey(key);
  }, [sortKey]);

  const clearSort = useCallback(() => { setSortKey(null); setSortAsc(false); }, []);

  const filtered = useMemo(
    () => filterSignals(signals, category, minAdvCr, metricsCache, subType, fnoOnly),
    [signals, category, minAdvCr, metricsCache, subType, fnoOnly],
  );

  const sortedFiltered = useMemo(() => {
    const q = query.trim().toUpperCase();
    const base = q ? filtered.filter(s => s.symbol.includes(q)) : filtered;
    if (!sortKey) return base;
    return [...base].sort((a, b) => {
      const ma = metricsCache[a.symbol]; const mb = metricsCache[b.symbol];
      let av: number | null = null; let bv: number | null = null;
      switch (sortKey) {
        case 'timestamp':  av = new Date(a.timestamp).getTime(); bv = new Date(b.timestamp).getTime(); break;
        case 'price':      av = a.price ?? null;      bv = b.price ?? null;      break;
        case 'volume_ratio': av = a.volume_ratio ?? null; bv = b.volume_ratio ?? null; break;
        case 'score':      av = a.score ?? null;      bv = b.score ?? null;      break;
        case 'adv':        av = ma?.adv_20_cr ?? null; bv = mb?.adv_20_cr ?? null; break;
        case 'chg_pct':    av = ma?.day_chg_pct ?? null; bv = mb?.day_chg_pct ?? null; break;
        case 'f52h_pct':
          av = ma?.week52_high != null && a.price != null ? (a.price / ma.week52_high - 1) * 100 : null;
          bv = mb?.week52_high != null && b.price != null ? (b.price / mb.week52_high - 1) * 100 : null;
          break;
      }
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return sortAsc ? av - bv : bv - av;
    });
  }, [filtered, query, sortKey, sortAsc, metricsCache]);

  return { query, setQuery, sortKey, sortAsc, handleSort, clearSort, filtered, sortedFiltered };
}
