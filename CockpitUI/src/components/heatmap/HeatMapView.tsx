'use client';

import { memo } from 'react';
import { HEAT_LEGEND } from '@/lib/heatmap';
import type { HeatMapEntry } from '@/lib/heatmap';
import { HeatMapCell } from './HeatMapCell';

interface HeatMapViewProps {
  entries:     HeatMapEntry[];
  onCellClick: (symbol: string) => void;
}

export const HeatMapView = memo(({ entries, onCellClick }: HeatMapViewProps) => (
  <div className="flex min-h-0 flex-1 flex-col">
    <div className="flex shrink-0 items-center gap-3 border-b border-border bg-panel/80 px-4 py-2">
      <span className="label-xs">Day Chg</span>
      {HEAT_LEGEND.map(l => (
        <span key={l.label} className="flex items-center gap-1 text-[10px] text-dim">
          <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: l.color }} />
          {l.label}
        </span>
      ))}
      <span className="ml-auto text-[10px] text-ghost">Cell size = ADV</span>
    </div>

    <div className="flex-1 overflow-auto p-2">
      {entries.length === 0 ? (
        <div className="flex h-32 items-center justify-center text-[12px] text-ghost">No data</div>
      ) : (
        <div className="flex flex-wrap content-start gap-1">
          {entries.map(e => (
            <HeatMapCell key={e.symbol} entry={e} onClick={onCellClick} />
          ))}
        </div>
      )}
    </div>
  </div>
));
HeatMapView.displayName = 'HeatMapView';
