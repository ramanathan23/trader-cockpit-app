'use client';

import { memo } from 'react';
import { RefreshCw, AlignJustify, LayoutGrid, BarChart2 } from 'lucide-react';
import { cn } from '@/lib/cn';
import { ScreenerPresetGroups } from '@/components/screener/ScreenerPresetGroups';
import type { ScreenerPreset } from '@/domain/screener';
import type { StockViewMode } from './useStockListState';

interface StockListFiltersProps {
  query:         string;
  fnoOnly:       boolean;
  presets:       Set<ScreenerPreset>;
  showPresets:   boolean;
  loading:       boolean;
  totalCount:    number;
  filteredCount: number;
  viewMode:      StockViewMode;
  onQuery:       (q: string) => void;
  onFnoOnly:     (v: boolean) => void;
  onPreset:      (p: ScreenerPreset) => void;
  onReset:       () => void;
  onRefresh:     () => void;
  onShowPresets: (v: boolean) => void;
  onViewMode:    (v: StockViewMode) => void;
}

const VIEW_BTNS: { mode: StockViewMode; icon: React.ReactNode; title: string }[] = [
  { mode: 'table',   icon: <AlignJustify size={12} />, title: 'Table' },
  { mode: 'card',    icon: <LayoutGrid   size={12} />, title: 'Cards' },
  { mode: 'chart',   icon: <BarChart2    size={12} />, title: 'Chart view' },
];

export const StockListFilters = memo((props: StockListFiltersProps) => {
  const {
    query, fnoOnly, presets, showPresets, loading,
    totalCount, filteredCount, viewMode,
    onQuery, onFnoOnly, onPreset, onReset, onRefresh, onShowPresets, onViewMode,
  } = props;
  const hasActive = !!query || fnoOnly || presets.size > 0;

  return (
    <div className="flex shrink-0 flex-col gap-2 border-b border-border bg-panel/80 px-4 py-3">
      <div className="flex items-center gap-2">
        <input
          className="field h-8 w-[200px]"
          placeholder="Search symbol or note…"
          value={query}
          onChange={e => onQuery(e.target.value)}
        />
        <button type="button"
          className={cn('seg-btn border border-border', fnoOnly && 'active text-violet')}
          onClick={() => onFnoOnly(!fnoOnly)}>
          F&O
        </button>
        <button type="button"
          className={cn('seg-btn border border-border', showPresets && 'active text-accent')}
          onClick={() => onShowPresets(!showPresets)}>
          Filters
          {presets.size > 0 && <span className="num ml-1 text-accent">{presets.size}</span>}
        </button>
        {hasActive && (
          <button type="button"
            className="seg-btn border border-border text-bear/80 hover:text-bear"
            onClick={onReset}>
            Reset
          </button>
        )}
        <span className="num ml-auto text-[11px] text-ghost">{filteredCount}/{totalCount}</span>
        <div className="seg-group">
          {VIEW_BTNS.map(v => (
            <button key={v.mode} type="button" title={v.title}
              className={cn('seg-btn px-2', viewMode === v.mode && 'active text-accent')}
              onClick={() => onViewMode(v.mode)}>
              {v.icon}
            </button>
          ))}
        </div>
        <button type="button"
          className="icon-btn h-7 w-7"
          title="Refresh"
          disabled={loading}
          onClick={onRefresh}>
          <RefreshCw size={13} className={cn(loading && 'animate-spin')} />
        </button>
      </div>
      {showPresets && (
        <div className="flex flex-wrap items-center gap-2">
          <ScreenerPresetGroups presets={presets} onPreset={onPreset} />
        </div>
      )}
    </div>
  );
});
StockListFilters.displayName = 'StockListFilters';
