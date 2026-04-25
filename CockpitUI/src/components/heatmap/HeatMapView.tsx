'use client';

import { memo, useEffect, useMemo, useRef, useState } from 'react';
import { hierarchy, treemap, treemapSquarify } from 'd3-hierarchy';
import { HEAT_LEGEND, HEATMAP_MIN_ADV_CR, HEATMAP_TOP_PER_SIDE, heatStats, heatWeight, topLiquidMovers } from '@/lib/heatmap';
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
  const visibleEntries = useMemo(() => topLiquidMovers(entries), [entries]);
  const stats = heatStats(visibleEntries);
  const avg = stats.avgMove;
  const mapRef = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (!mapRef.current) return;
    const observer = new ResizeObserver(([entry]) => {
      const rect = entry.contentRect;
      setSize({
        width:  Math.floor(rect.width),
        height: Math.floor(rect.height),
      });
    });
    observer.observe(mapRef.current);
    return () => observer.disconnect();
  }, []);

  const nodes = useMemo(() => {
    if (size.width <= 0 || size.height <= 0 || visibleEntries.length === 0) return [];
    const root = hierarchy<{ children: HeatMapEntry[] } | HeatMapEntry>({ children: visibleEntries })
      .sum(node => {
        if (!('symbol' in node)) return 0;
        return heatWeight(node.chgPct);
      })
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));

    const laidOut = treemap<typeof root.data>()
      .size([size.width, size.height])
      .paddingInner(3)
      .paddingOuter(0)
      .tile(treemapSquarify.ratio(1.2))
      .round(true)(root);

    return laidOut.leaves()
      .filter(node => 'symbol' in node.data)
      .map(node => ({
        entry: node.data as HeatMapEntry,
        x: node.x0,
        y: node.y0,
        w: Math.max(0, node.x1 - node.x0),
        h: Math.max(0, node.y1 - node.y0),
      }));
  }, [visibleEntries, size]);

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-base">
      <div className="shrink-0 border-b border-border bg-panel/90 px-4 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="mr-1">
            <div className="label-xs">Top Movers</div>
            <div className="num text-[18px] font-black leading-tight text-fg">{visibleEntries.length}</div>
          </div>
          <Metric label="Gainers" value={stats.gainers} tone="text-bull" />
          <Metric label="Losers" value={stats.losers} tone="text-bear" />
          <Metric label="Flat" value={stats.flat} tone="text-dim" />
          <Metric label="Avg" value={avg == null ? '-' : `${avg > 0 ? '+' : ''}${avg.toFixed(2)}%`} tone={avg == null ? 'text-dim' : avg >= 0 ? 'text-bull' : 'text-bear'} />
          <Metric label="Min ADV" value={`${HEATMAP_MIN_ADV_CR}Cr`} tone="text-dim" />
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-bold text-ghost">{HEATMAP_TOP_PER_SIDE}+{HEATMAP_TOP_PER_SIDE}</span>
            {HEAT_LEGEND.map(l => (
              <span key={l.label} className="flex items-center gap-1 text-[10px] font-bold text-dim">
                <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: l.color }} />
                {l.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="relative min-h-[360px] flex-1 overflow-hidden">
        <div ref={mapRef} className="absolute inset-3">
          {visibleEntries.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-[12px] text-ghost">No liquid movers</div>
          ) : nodes.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-[12px] text-ghost">Sizing heatmap</div>
          ) : (
            nodes.map(node => (
              <div
                key={node.entry.symbol}
                className="absolute"
                style={{
                  transform: `translate(${node.x}px, ${node.y}px)`,
                  width:     node.w,
                  height:    node.h,
                }}
              >
                <HeatMapCell
                  entry={node.entry}
                  onClick={onCellClick}
                  width={node.w}
                  height={node.h}
                />
              </div>
            ))
          )}
        </div>
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
