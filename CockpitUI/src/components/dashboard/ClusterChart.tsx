'use client';

import { useState, useRef, useMemo } from 'react';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import type { ScoredSymbol } from '@/domain/dashboard';
import { axisTicks, mkToX, mkToY, W, H } from '@/lib/clusterUtils';
import { useClusterPanZoom } from './useClusterPanZoom';
import { ClusterBackground } from './ClusterBackground';
import { ClusterDots } from './ClusterDots';
import { ClusterTooltip } from './ClusterTooltip';
import { SymbolModal } from './SymbolModal';

interface ClusterChartProps { scores: ScoredSymbol[]; loading: boolean; }

const LEGEND_ITEMS = [
  ['rgb(var(--bull))', 'Bullish'],
  ['rgb(var(--bear))', 'Bearish'],
  ['rgb(var(--amber))', 'Neutral'],
] as const;

export function ClusterChart({ scores, loading }: ClusterChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredRow, setHoveredRow] = useState<ScoredSymbol | null>(null);
  const [mousePos,   setMousePos]   = useState({ x: 0, y: 0 });
  const [selected,   setSelected]   = useState<string | null>(null);

  const plotable = useMemo(() => scores.filter(s => s.comfort_score != null), [scores]);
  const { svgRef, viewBounds, setViewBounds, autoBounds, isDraggingRef, cancelDrag, zoomCenter, handleWheel, handlePointerDown, handlePointerMove, handlePointerUp } = useClusterPanZoom(plotable, scores);

  if (loading) return <div className="flex flex-1 items-center justify-center text-[13px] text-dim">Computing cluster…</div>;

  const bounds = viewBounds ?? autoBounds;
  const toX    = mkToX(bounds);
  const toY    = mkToY(bounds);

  return (
    <div ref={containerRef} className="relative flex flex-1 flex-col overflow-hidden"
      onMouseMove={e => { const r = containerRef.current?.getBoundingClientRect(); if (r) setMousePos({ x: e.clientX - r.left, y: e.clientY - r.top }); }}>

      <div className="absolute right-2 top-2 z-10 flex gap-1">
        <button type="button" className="icon-btn h-7 w-7" title="Zoom in"     onClick={() => zoomCenter(0.75)}><ZoomIn    size={12} /></button>
        <button type="button" className="icon-btn h-7 w-7" title="Zoom out"    onClick={() => zoomCenter(1.33)}><ZoomOut   size={12} /></button>
        <button type="button" className="icon-btn h-7 w-7" title="Fit to data" onClick={() => setViewBounds(null)}><Maximize2 size={12} /></button>
      </div>

      <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} className="h-full w-full"
        style={{ userSelect: 'none', cursor: isDraggingRef.current ? 'grabbing' : 'crosshair' }}
        onMouseLeave={() => { setHoveredRow(null); cancelDrag(); }}
        onWheel={handleWheel} onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove} onPointerUp={handlePointerUp}>
        <ClusterBackground bounds={bounds} xTicks={axisTicks(bounds.x0, bounds.x1)} yTicks={axisTicks(bounds.y0, bounds.y1)} toX={toX} toY={toY} />
        <ClusterDots plotable={plotable} scores={scores} bounds={bounds} toX={toX} toY={toY}
          hoveredRow={hoveredRow} setHoveredRow={setHoveredRow}
          selected={selected} setSelected={setSelected} isDraggingRef={isDraggingRef} />
      </svg>

      <ClusterTooltip hoveredRow={hoveredRow} mousePos={mousePos} containerRef={containerRef} />
      {selected && <SymbolModal symbol={selected} initialTab="chart" onClose={() => setSelected(null)} />}

      <div className="flex shrink-0 items-center gap-4 border-t border-border bg-panel/80 px-4 py-2 text-[10px]">
        <span className="font-black uppercase text-ghost">Legend</span>
        {LEGEND_ITEMS.map(([color, label]) => (
          <span key={label} className="flex items-center gap-1.5">
            <svg width={10} height={10}><circle cx={5} cy={5} r={4} fill={color} fillOpacity={0.7} /></svg>
            <span className="text-ghost">{label}</span>
          </span>
        ))}
        <span className="text-ghost">· dot size = total score · scroll/buttons to zoom · drag to pan · click dot for chart</span>
        <span className="ml-auto num text-ghost">{plotable.length} plotted</span>
      </div>
    </div>
  );
}
