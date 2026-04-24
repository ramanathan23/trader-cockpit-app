'use client';

import { memo, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { cn } from '@/lib/cn';
import { isRangeActive, type ScreenerPreset, type ScreenerRangeFilter } from '@/domain/screener';
import { ScreenerPresetGroups } from './ScreenerPresetGroups';
import { ScreenerRangePanel } from './ScreenerRangePanel';

const ADV_TIERS = [
  { label: 'All', cr: 0 }, { label: '5Cr+', cr: 5 }, { label: '25Cr+', cr: 25 },
  { label: '100Cr+', cr: 100 }, { label: '500Cr+', cr: 500 },
];

interface ScreenerFiltersProps {
  query: string;          onQuery: (q: string) => void;
  range: ScreenerRangeFilter; onRange: (r: ScreenerRangeFilter) => void;
  presets: Set<ScreenerPreset>; onPreset: (p: ScreenerPreset) => void;
  fnoOnly: boolean;       onFnoOnly: (v: boolean) => void;
  onReset: () => void;
  totalCount: number;     filteredCount: number;
  loading: boolean;       onRefresh: () => void;
}

export const ScreenerFilters = memo(({ query, onQuery, range, onRange, presets, onPreset, fnoOnly, onFnoOnly, onReset, totalCount, filteredCount, loading, onRefresh }: ScreenerFiltersProps) => {
  const [expanded, setExpanded] = useState(false);
  const rangeActive = isRangeActive(range, fnoOnly);
  const hasFilters  = Boolean(query) || rangeActive || presets.size > 0;
  const advMin      = range.advMin;

  return (
    <div className="shrink-0 border-b border-border bg-panel/78">
      <div className="flex flex-wrap items-center gap-3 px-4 py-3">
        <input type="text" value={query} onChange={e => onQuery(e.target.value)}
          placeholder="Search symbol" className="field w-44 text-[12px]" />

        <div className="seg-group">
          {ADV_TIERS.map(tier => (
            <button key={tier.cr} type="button" onClick={() => onRange({ ...range, advMin: tier.cr, advMax: Infinity })}
              className={cn('seg-btn', advMin === tier.cr && range.advMax === Infinity && 'active text-amber')}>
              {tier.label}
            </button>
          ))}
        </div>

        <button type="button" onClick={() => onFnoOnly(!fnoOnly)}
          className={cn('seg-btn border border-border', fnoOnly && 'active text-violet')}>F&O</button>

        <ScreenerPresetGroups presets={presets} onPreset={onPreset} />

        <div className="ml-auto flex items-center gap-2">
          <button type="button" onClick={() => setExpanded(v => !v)}
            className={`h-8 rounded-lg border px-3 text-[11px] font-black transition-colors ${
              expanded || rangeActive ? 'border-accent/45 bg-accent/10 text-accent' : 'border-border bg-base/50 text-dim hover:border-rim hover:text-fg'
            }`}>
            {expanded ? 'Hide filters' : 'More filters'}
          </button>
          {hasFilters && (
            <button type="button" onClick={onReset}
              className="h-8 rounded-lg border border-border bg-base/50 px-3 text-[11px] font-bold text-dim hover:border-bear/50 hover:text-bear">
              Reset
            </button>
          )}
          <span className="chip num hidden sm:inline-flex">{filteredCount}/{totalCount}</span>
          <button type="button" onClick={onRefresh} disabled={loading} className="icon-btn" title="Refresh screener">
            <RotateCcw size={15} />
          </button>
        </div>
      </div>

      {expanded && <ScreenerRangePanel range={range} onRange={onRange} />}
    </div>
  );
});
ScreenerFilters.displayName = 'ScreenerFilters';
