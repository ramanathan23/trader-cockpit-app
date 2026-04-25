'use client';

import { memo } from 'react';
import { HEAT_LEGEND, heatStats } from '@/lib/heatmap';
import type { HeatMapEntry } from '@/lib/heatmap';
import { HeatMapCell } from './HeatMapCell';

interface HeatMapViewProps {
  entries:     HeatMapEntry[];
  onCellClick: (symbol: string) => void;
}

export const HeatMapView = memo(({ entries, onCellClick }: HeatMapViewProps) => (
  <HeatMapFrame entries={entries} onCellClick={onCellClick} />
));
HeatMapView.displayName = 'HeatMapView';

function HeatMapFrame({ entries, onCellClick }: HeatMapViewProps) {
  const stats = heatStats(entries);
  const avg = stats.avgMove;

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-base">
      <div className="shrink-0 border-b border-border bg-panel/90 px-4 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="mr-1">
            <div className="label-xs">Heatmap</div>
            <div className="num text-[18px] font-black leading-tight text-fg">{entries.length}</div>
          </div>
          <Metric label="Gainers" value={stats.gainers} tone="text-bull" />
          <Metric label="Losers" value={stats.losers} tone="text-bear" />
          <Metric label="Flat" value={stats.flat} tone="text-dim" />
          <Metric label="Avg" value={avg == null ? '-' : `${avg > 0 ? '+' : ''}${avg.toFixed(2)}%`} tone={avg == null ? 'text-dim' : avg >= 0 ? 'text-bull' : 'text-bear'} />
          <div className="ml-auto flex flex-wrap items-center gap-2">
            {HEAT_LEGEND.map(l => (
              <span key={l.label} className="flex items-center gap-1 text-[10px] font-bold text-dim">
                <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: l.color }} />
                {l.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-3">
        {entries.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-[12px] text-ghost">No data</div>
        ) : (
          <div className="flex flex-wrap content-start gap-1.5">
            {entries.map(e => (
              <HeatMapCell key={e.symbol} entry={e} onClick={onCellClick} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: number | string; tone: string }) {
  return (
    <div className="min-w-[64px] border-l border-border/80 pl-3">
      <div className="label-xs">{label}</div>
      <div className={`num text-[14px] font-black leading-tight ${tone}`}>{value}</div>
    </div>
  );
}
