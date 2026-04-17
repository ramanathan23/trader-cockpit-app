'use client';

import { memo, useState } from 'react';
import {
  DEFAULT_RANGE, SCREENER_PRESETS, isRangeActive,
  type ScreenerPreset, type ScreenerRangeFilter,
} from '@/domain/screener';
import { ViewToggle } from '@/components/ui/ViewToggle';

const ADV_TIERS = [
  { label: 'All',    cr: 0   },
  { label: '5Cr+',   cr: 5   },
  { label: '25Cr+',  cr: 25  },
  { label: '100Cr+', cr: 100 },
  { label: '500Cr+', cr: 500 },
];

interface ScreenerFiltersProps {
  query:        string;
  onQuery:      (q: string) => void;
  range:        ScreenerRangeFilter;
  onRange:      (r: ScreenerRangeFilter) => void;
  presets:      Set<ScreenerPreset>;
  onPreset:     (p: ScreenerPreset) => void;
  fnoOnly:      boolean;
  onFnoOnly:    (v: boolean) => void;
  onReset:      () => void;
  totalCount:   number;
  filteredCount: number;
  loading:      boolean;
  onRefresh:    () => void;
  viewMode:     'card' | 'table';
  onViewMode:   (v: 'card' | 'table') => void;
}

function RangeInput({
  label, field, min, unit = '', range, onRange, placeholder = '∞',
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
    <span className="flex items-center gap-1 text-[10px] text-muted">
      {label}
      <input
        type="number"
        value={displayVal}
        placeholder={placeholder}
        className="w-16 bg-base border border-border rounded px-1.5 py-0.5 text-fg text-[10px] tabular-nums focus:outline-none focus:border-[#58a6ff] [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
        onChange={e => {
          const raw = e.target.value;
          const parsed = raw === '' ? (min ? 0 : Infinity) : parseFloat(raw);
          onRange({ ...range, [field]: isNaN(parsed) ? (min ? 0 : Infinity) : parsed });
        }}
      />
      {unit && <span>{unit}</span>}
    </span>
  );
}

export const ScreenerFilters = memo(({
  query, onQuery, range, onRange, presets, onPreset, fnoOnly, onFnoOnly, onReset,
  totalCount, filteredCount, loading, onRefresh, viewMode, onViewMode,
}: ScreenerFiltersProps) => {
  const [expanded, setExpanded] = useState(false);
  const rangeActive = isRangeActive(range, fnoOnly);
  const hasFilters = query || rangeActive || presets.size > 0;

  // Quick ADV tier — sets advMin and clears advMax
  const advMin = range.advMin;
  const setAdvTier = (cr: number) => onRange({ ...range, advMin: cr, advMax: Infinity });

  return (
    <div className="shrink-0 bg-surface border-b border-subtle z-10">
      {/* ── Primary filter row ── */}
      <div className="flex items-center flex-wrap gap-2 px-4 py-1.5">
        {/* Symbol search */}
        <input
          type="text"
          value={query}
          onChange={e => onQuery(e.target.value)}
          placeholder="Search symbol…"
          className="bg-subtle border border-border text-fg text-xs rounded px-2 py-1 w-36 focus:outline-none focus:border-[#58a6ff]"
        />

        {/* ADV tier quick-filter */}
        <div className="flex items-center gap-1">
          <span className="text-muted text-[10px]">ADV</span>
          {ADV_TIERS.map(t => (
            <button
              key={t.cr}
              onClick={() => setAdvTier(t.cr)}
              className={`text-[10px] font-bold px-2 py-1 rounded border transition-colors ${
                advMin === t.cr && range.advMax === Infinity
                  ? 'bg-[#1a2233] border-[#58a6ff] text-[#58a6ff]'
                  : 'bg-subtle border-border text-muted hover:border-[#58a6ff] hover:text-fg'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* FNO toggle */}
        <button
          onClick={() => onFnoOnly(!fnoOnly)}
          className={`text-[10px] font-bold px-2 py-1 rounded border transition-colors ${
            fnoOnly
              ? 'bg-[#2d1f3a] border-[#c678dd] text-[#c678dd]'
              : 'bg-subtle border-border text-muted hover:border-[#c678dd] hover:text-fg'
          }`}
        >
          F&amp;O
        </button>

        {/* Preset tags — multi-select AND logic */}
        <div className="flex items-center gap-1">
          {SCREENER_PRESETS.map(p => (
            <button
              key={p.key}
              onClick={() => onPreset(p.key)}
              className={`text-[10px] font-bold px-2 py-1 rounded border transition-colors ${
                presets.has(p.key)
                  ? 'bg-[#2d2118] border-[#d29922] text-[#d29922]'
                  : 'bg-subtle border-border text-muted hover:border-[#d29922] hover:text-fg'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 ml-auto">
          {/* Advanced filter toggle */}
          <button
            onClick={() => setExpanded(x => !x)}
            className={`text-[10px] font-bold px-2 py-1 rounded border transition-colors ${
              expanded || rangeActive
                ? 'bg-[#1a2233] border-[#58a6ff] text-[#58a6ff]'
                : 'bg-subtle border-border text-muted hover:border-[#58a6ff] hover:text-fg'
            }`}
          >
            {expanded ? '▲ FILTERS' : '▼ FILTERS'}
            {rangeActive && <span className="ml-1 text-[9px] bg-[#58a6ff] text-base px-1 rounded-full">•</span>}
          </button>

          {/* Clear all */}
          {hasFilters && (
            <button
              onClick={onReset}
              className="text-[10px] text-muted hover:text-[#f85149] border border-border hover:border-[#f85149] px-2 py-1 rounded transition-colors"
            >
              RESET
            </button>
          )}

          {/* Count */}
          <span className="text-muted text-[10px] tabular-nums hidden sm:block">
            {filteredCount} / {totalCount}
          </span>

          {/* Refresh */}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="text-[10px] font-bold px-2.5 py-1 rounded border border-border text-muted hover:border-[#58a6ff] hover:text-[#58a6ff] transition-colors disabled:opacity-40"
          >
            {loading ? 'Loading…' : '↻ Refresh'}
          </button>

          {/* View toggle */}
          <ViewToggle view={viewMode} onChange={onViewMode} />
        </div>
      </div>

      {/* ── Advanced range filter row ── */}
      {expanded && (
        <div className="flex items-center flex-wrap gap-x-6 gap-y-2 px-4 py-2 border-t border-subtle bg-base/50 animate-slide-in">
          {/* ATR */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-muted font-bold tracking-wide">ATR</span>
            <RangeInput label="min" field="atrMin" min  range={range} onRange={onRange} placeholder="0" />
            <span className="text-border text-[10px]">—</span>
            <RangeInput label="max" field="atrMax" range={range} onRange={onRange} />
          </div>

          {/* CLOSE price */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-muted font-bold tracking-wide">CLOSE</span>
            <RangeInput label="min" field="closeMin" min  range={range} onRange={onRange} placeholder="0" />
            <span className="text-border text-[10px]">—</span>
            <RangeInput label="max" field="closeMax" range={range} onRange={onRange} />
          </div>

          {/* ADV range (fine-grained) */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-muted font-bold tracking-wide">ADV Cr</span>
            <RangeInput label="min" field="advMin" min range={range} onRange={onRange} placeholder="0" />
            <span className="text-border text-[10px]">—</span>
            <RangeInput label="max" field="advMax" range={range} onRange={onRange} unit="Cr" />
          </div>

          {/* 52H% — distance from 52-week high */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-muted font-bold tracking-wide">52H%</span>
            <RangeInput label="from" field="f52hMin" range={range} onRange={onRange} placeholder="-∞" />
            <span className="text-border text-[10px]">—</span>
            <RangeInput label="to"   field="f52hMax" range={range} onRange={onRange} placeholder="0" />
            <span className="text-muted text-[10px]">%</span>
          </div>

          {/* 52L% — distance from 52-week low */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-muted font-bold tracking-wide">52L%</span>
            <RangeInput label="from" field="f52lMin" min range={range} onRange={onRange} placeholder="0" />
            <span className="text-border text-[10px]">—</span>
            <RangeInput label="to"   field="f52lMax" range={range} onRange={onRange} />
            <span className="text-muted text-[10px]">%</span>
          </div>

          <button
            onClick={() => onRange(DEFAULT_RANGE)}
            className="text-[10px] text-muted hover:text-[#f85149] transition-colors ml-2"
          >
            Reset ranges
          </button>
        </div>
      )}
    </div>
  );
});

ScreenerFilters.displayName = 'ScreenerFilters';
