'use client';

import { memo, useState } from 'react';
import {
  DEFAULT_RANGE,
  SCREENER_PRESETS,
  isRangeActive,
  type ScreenerPreset,
  type ScreenerRangeFilter,
} from '@/domain/screener';
import { ViewToggle } from '@/components/ui/ViewToggle';

const ADV_TIERS = [
  { label: 'All', cr: 0 },
  { label: '5Cr+', cr: 5 },
  { label: '25Cr+', cr: 25 },
  { label: '100Cr+', cr: 100 },
  { label: '500Cr+', cr: 500 },
];

interface ScreenerFiltersProps {
  query: string;
  onQuery: (q: string) => void;
  range: ScreenerRangeFilter;
  onRange: (r: ScreenerRangeFilter) => void;
  presets: Set<ScreenerPreset>;
  onPreset: (p: ScreenerPreset) => void;
  fnoOnly: boolean;
  onFnoOnly: (v: boolean) => void;
  onReset: () => void;
  totalCount: number;
  filteredCount: number;
  loading: boolean;
  onRefresh: () => void;
  viewMode: 'card' | 'table';
  onViewMode: (v: 'card' | 'table') => void;
}

function RangeInput({
  label,
  field,
  min,
  unit = '',
  range,
  onRange,
  placeholder = 'inf',
}: {
  label: string;
  field: keyof ScreenerRangeFilter;
  min?: boolean;
  unit?: string;
  range: ScreenerRangeFilter;
  onRange: (r: ScreenerRangeFilter) => void;
  placeholder?: string;
}) {
  const val = range[field];
  const displayVal = (val === Infinity || val === -Infinity) ? '' : String(val);

  return (
    <span className="flex items-center gap-1 text-[11px] text-ghost">
      {label}
      <input
        type="number"
        value={displayVal}
        placeholder={placeholder}
        className="field h-8 w-20 text-[11px]"
        onChange={event => {
          const raw = event.target.value;
          const parsed = raw === '' ? (min ? 0 : Infinity) : parseFloat(raw);
          onRange({ ...range, [field]: Number.isNaN(parsed) ? (min ? 0 : Infinity) : parsed });
        }}
      />
      {unit && <span>{unit}</span>}
    </span>
  );
}

export const ScreenerFilters = memo(({
  query,
  onQuery,
  range,
  onRange,
  presets,
  onPreset,
  fnoOnly,
  onFnoOnly,
  onReset,
  totalCount,
  filteredCount,
  loading,
  onRefresh,
  viewMode,
  onViewMode,
}: ScreenerFiltersProps) => {
  const [expanded, setExpanded] = useState(false);
  const rangeActive = isRangeActive(range, fnoOnly);
  const hasFilters = Boolean(query) || rangeActive || presets.size > 0;
  const advMin = range.advMin;

  const setAdvTier = (cr: number) => onRange({ ...range, advMin: cr, advMax: Infinity });

  return (
    <div className="shrink-0 border-b border-border bg-panel/78">
      <div className="flex flex-wrap items-center gap-3 px-4 py-3">
        <input
          type="text"
          value={query}
          onChange={event => onQuery(event.target.value)}
          placeholder="Search symbol"
          className="field w-44 text-[12px]"
        />

        <div className="seg-group">
          {ADV_TIERS.map(tier => (
            <button
              key={tier.cr}
              type="button"
              onClick={() => setAdvTier(tier.cr)}
              className={`seg-btn ${advMin === tier.cr && range.advMax === Infinity ? 'active' : ''}`}
              style={advMin === tier.cr && range.advMax === Infinity ? { color: 'rgb(var(--amber))' } : undefined}
            >
              {tier.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() => onFnoOnly(!fnoOnly)}
          className={`seg-btn border border-border ${fnoOnly ? 'active' : ''}`}
          style={fnoOnly ? { color: 'rgb(var(--violet))' } : undefined}
        >
          F&O
        </button>

        <div className="seg-group">
          {SCREENER_PRESETS.filter(preset => !preset.group).map(preset => (
            <button
              key={preset.key}
              type="button"
              onClick={() => onPreset(preset.key)}
              className={`seg-btn ${presets.has(preset.key) ? 'active' : ''}`}
              style={presets.has(preset.key) ? { color: 'rgb(var(--accent))' } : undefined}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <div className="seg-group">
          {SCREENER_PRESETS.filter(preset => preset.group === 'cam').map(preset => (
            <button
              key={preset.key}
              type="button"
              onClick={() => onPreset(preset.key)}
              className={`seg-btn ${presets.has(preset.key) ? 'active' : ''}`}
              style={presets.has(preset.key) ? { color: 'rgb(var(--violet))' } : undefined}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={() => setExpanded(value => !value)}
            className={`h-8 rounded-lg border px-3 text-[11px] font-black transition-colors ${
              expanded || rangeActive
                ? 'border-accent/45 bg-accent/10 text-accent'
                : 'border-border bg-base/50 text-dim hover:border-rim hover:text-fg'
            }`}
          >
            {expanded ? 'Hide filters' : 'More filters'}
          </button>

          {hasFilters && (
            <button
              type="button"
              onClick={onReset}
              className="h-8 rounded-lg border border-border bg-base/50 px-3 text-[11px] font-bold text-dim hover:border-bear/50 hover:text-bear"
            >
              Reset
            </button>
          )}

          <span className="chip num hidden sm:inline-flex">{filteredCount}/{totalCount}</span>

          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            className="icon-btn"
            title="Refresh screener"
            aria-label="Refresh screener"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M20 12a8 8 0 0 1-13.7 5.7M4 12A8 8 0 0 1 17.7 6.3M18 3v4h-4M6 21v-4h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>

          <ViewToggle view={viewMode} onChange={onViewMode} />
        </div>
      </div>

      {expanded && (
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-border bg-base/35 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-black uppercase text-ghost">ATR</span>
            <RangeInput label="min" field="atrMin" min range={range} onRange={onRange} placeholder="0" />
            <RangeInput label="max" field="atrMax" range={range} onRange={onRange} />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-black uppercase text-ghost">Close</span>
            <RangeInput label="min" field="closeMin" min range={range} onRange={onRange} placeholder="0" />
            <RangeInput label="max" field="closeMax" range={range} onRange={onRange} />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-black uppercase text-ghost">ADV</span>
            <RangeInput label="min" field="advMin" min range={range} onRange={onRange} placeholder="0" />
            <RangeInput label="max" field="advMax" range={range} onRange={onRange} unit="Cr" />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-black uppercase text-ghost">52H%</span>
            <RangeInput label="from" field="f52hMin" range={range} onRange={onRange} placeholder="-inf" />
            <RangeInput label="to" field="f52hMax" range={range} onRange={onRange} placeholder="0" />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-black uppercase text-ghost">52L%</span>
            <RangeInput label="from" field="f52lMin" min range={range} onRange={onRange} placeholder="0" />
            <RangeInput label="to" field="f52lMax" range={range} onRange={onRange} />
          </div>

          <button type="button" onClick={() => onRange(DEFAULT_RANGE)} className="text-[11px] font-bold text-ghost hover:text-fg">
            Reset ranges
          </button>
        </div>
      )}
    </div>
  );
});

ScreenerFilters.displayName = 'ScreenerFilters';
