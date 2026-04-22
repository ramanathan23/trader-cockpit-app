'use client';

import { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import type { ScoredSymbol } from '@/domain/dashboard';
import { SymbolModal } from './SymbolModal';

const W = 900;
const H = 540;
const PAD = { top: 32, right: 28, bottom: 52, left: 56 };
const PW = W - PAD.left - PAD.right;
const PH = H - PAD.top - PAD.bottom;

const QUAD_TOTAL = 65;
const QUAD_COMFORT = 65;

interface ViewBounds { x0: number; x1: number; y0: number; y1: number; }

function dotColor(row: ScoredSymbol): string {
  if (row.weekly_bias === 'BULLISH') return 'rgb(var(--bull))';
  if (row.weekly_bias === 'BEARISH') return 'rgb(var(--bear))';
  return 'rgb(var(--amber))';
}

function dotRadius(totalScore: number): number {
  return Math.min(14, Math.max(4, 4 + (totalScore / 100) * 10));
}

function comfortColor(v: number | null | undefined): string {
  if (v == null) return 'rgb(var(--ghost))';
  if (v >= 80) return 'rgb(var(--bull))';
  if (v >= 65) return 'rgb(var(--accent))';
  if (v >= 50) return 'rgb(var(--amber))';
  return 'rgb(var(--bear))';
}

function axisTicks(min: number, max: number): number[] {
  const range = max - min;
  const step = range <= 15 ? 2 : range <= 30 ? 5 : range <= 60 ? 10 : 25;
  const first = Math.ceil(min / step) * step;
  const ticks: number[] = [];
  for (let v = first; v <= max + 0.001; v += step) ticks.push(Math.round(v));
  return ticks;
}

interface ClusterChartProps {
  scores: ScoredSymbol[];
  loading: boolean;
}

export function ClusterChart({ scores, loading }: ClusterChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredRow, setHoveredRow] = useState<ScoredSymbol | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [selected, setSelected] = useState<string | null>(null);
  const [viewBounds, setViewBounds] = useState<ViewBounds | null>(null);

  // drag pan state via refs to avoid stale closures in pointer handlers
  const dragAnchorRef = useRef<{ svgX: number; svgY: number; bounds: ViewBounds } | null>(null);
  const isDraggingRef = useRef(false);

  const plotable = useMemo(() => scores.filter(s => s.comfort_score != null), [scores]);

  const autoBounds = useMemo<ViewBounds>(() => {
    if (plotable.length === 0) return { x0: 0, x1: 100, y0: 0, y1: 100 };
    const xs = plotable.map(d => d.total_score);
    const ys = plotable.map(d => d.comfort_score!);
    const xRange = Math.max(...xs) - Math.min(...xs);
    const yRange = Math.max(...ys) - Math.min(...ys);
    const xpad = Math.max(4, xRange * 0.12);
    const ypad = Math.max(4, yRange * 0.12);
    return {
      x0: Math.max(0, Math.min(...xs) - xpad),
      x1: Math.min(100, Math.max(...xs) + xpad),
      y0: Math.max(0, Math.min(...ys) - ypad),
      y1: Math.min(100, Math.max(...ys) + ypad),
    };
  }, [plotable]);

  const bounds = viewBounds ?? autoBounds;

  // reset zoom when scores change
  useEffect(() => { setViewBounds(null); }, [scores]);

  function toX(v: number) { return PAD.left + ((v - bounds.x0) / (bounds.x1 - bounds.x0)) * PW; }
  function toY(v: number) { return PAD.top + (1 - (v - bounds.y0) / (bounds.y1 - bounds.y0)) * PH; }

  const clientToSvgCoords = useCallback((clientX: number, clientY: number) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const rect = svg.getBoundingClientRect();
    return {
      x: ((clientX - rect.left) / rect.width) * W,
      y: ((clientY - rect.top) / rect.height) * H,
    };
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent<SVGSVGElement>) => {
    e.preventDefault();
    const { x: svgX, y: svgY } = clientToSvgCoords(e.clientX, e.clientY);
    setViewBounds(prev => {
      const cur = prev ?? autoBounds;
      const focusX = cur.x0 + ((svgX - PAD.left) / PW) * (cur.x1 - cur.x0);
      const focusY = cur.y0 + (1 - (svgY - PAD.top) / PH) * (cur.y1 - cur.y0);
      const factor = e.deltaY > 0 ? 1.15 : 0.87;
      const nx0 = Math.max(0, focusX - (focusX - cur.x0) * factor);
      const nx1 = Math.min(100, focusX + (cur.x1 - focusX) * factor);
      const ny0 = Math.max(0, focusY - (focusY - cur.y0) * factor);
      const ny1 = Math.min(100, focusY + (cur.y1 - focusY) * factor);
      if (nx1 - nx0 < 1 || ny1 - ny0 < 1) return prev ?? autoBounds;
      return { x0: nx0, x1: nx1, y0: ny0, y1: ny1 };
    });
  }, [clientToSvgCoords, autoBounds]);

  const handlePointerDown = useCallback((e: React.PointerEvent<SVGSVGElement>) => {
    if (e.button !== 0) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    const { x, y } = clientToSvgCoords(e.clientX, e.clientY);
    dragAnchorRef.current = { svgX: x, svgY: y, bounds: viewBounds ?? autoBounds };
    isDraggingRef.current = false;
  }, [clientToSvgCoords, viewBounds, autoBounds]);

  const handlePointerMove = useCallback((e: React.PointerEvent<SVGSVGElement>) => {
    if (!dragAnchorRef.current) return;
    const { x: svgX, y: svgY } = clientToSvgCoords(e.clientX, e.clientY);
    const dx = svgX - dragAnchorRef.current.svgX;
    const dy = svgY - dragAnchorRef.current.svgY;
    if (!isDraggingRef.current && Math.abs(dx) < 4 && Math.abs(dy) < 4) return;
    isDraggingRef.current = true;
    const b = dragAnchorRef.current.bounds;
    const dxData = (dx / PW) * (b.x1 - b.x0);
    const dyData = -(dy / PH) * (b.y1 - b.y0);
    const nx0 = Math.max(0, b.x0 - dxData);
    const nx1 = Math.min(100, b.x1 - dxData);
    const ny0 = Math.max(0, b.y0 - dyData);
    const ny1 = Math.min(100, b.y1 - dyData);
    if (nx0 < nx1 && ny0 < ny1) {
      setViewBounds({ x0: nx0, x1: nx1, y0: ny0, y1: ny1 });
      dragAnchorRef.current = { svgX, svgY, bounds: { x0: nx0, x1: nx1, y0: ny0, y1: ny1 } };
    }
  }, [clientToSvgCoords]);

  const handlePointerUp = useCallback(() => {
    dragAnchorRef.current = null;
    // keep isDraggingRef.current = true briefly so onClick can check
    setTimeout(() => { isDraggingRef.current = false; }, 50);
  }, []);

  const zoomCenter = useCallback((factor: number) => {
    setViewBounds(prev => {
      const cur = prev ?? autoBounds;
      const cx = (cur.x0 + cur.x1) / 2;
      const cy = (cur.y0 + cur.y1) / 2;
      const nx0 = Math.max(0, cx - (cx - cur.x0) * factor);
      const nx1 = Math.min(100, cx + (cur.x1 - cx) * factor);
      const ny0 = Math.max(0, cy - (cy - cur.y0) * factor);
      const ny1 = Math.min(100, cy + (cur.y1 - cy) * factor);
      // prevent degenerate (zero-width) bounds on extreme zoom-in
      if (nx1 - nx0 < 1 || ny1 - ny0 < 1) return prev ?? autoBounds;
      return { x0: nx0, x1: nx1, y0: ny0, y1: ny1 };
    });
  }, [autoBounds]);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center text-[13px] text-dim">
        Computing cluster…
      </div>
    );
  }

  const xTicks = axisTicks(bounds.x0, bounds.x1);
  const yTicks = axisTicks(bounds.y0, bounds.y1);

  const ttW = 220;
  const ttH = 140;
  const containerW = containerRef.current?.offsetWidth ?? 900;
  const containerH = containerRef.current?.offsetHeight ?? 540;
  const ttLeft = Math.min(Math.max(4, mousePos.x + 18), containerW - ttW - 8);
  const ttTop = Math.min(Math.max(4, mousePos.y - ttH / 2), containerH - ttH - 32);

  return (
    <div
      ref={containerRef}
      className="relative flex flex-1 flex-col overflow-hidden"
      onMouseMove={e => {
        const rect = containerRef.current?.getBoundingClientRect();
        if (rect) setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
      }}
    >
      {/* zoom controls */}
      <div className="absolute right-2 top-2 z-10 flex gap-1">
        <button type="button" className="icon-btn h-7 w-7" title="Zoom in" onClick={() => zoomCenter(0.75)}>
          <ZoomIn size={12} aria-hidden="true" />
        </button>
        <button type="button" className="icon-btn h-7 w-7" title="Zoom out" onClick={() => zoomCenter(1.33)}>
          <ZoomOut size={12} aria-hidden="true" />
        </button>
        <button type="button" className="icon-btn h-7 w-7" title="Fit to data" onClick={() => setViewBounds(null)}>
          <Maximize2 size={12} aria-hidden="true" />
        </button>
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="h-full w-full"
        style={{ userSelect: 'none', cursor: isDraggingRef.current ? 'grabbing' : 'crosshair' }}
        onMouseLeave={() => { setHoveredRow(null); dragAnchorRef.current = null; }}
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
      >
        <defs>
          <clipPath id="plot-area">
            <rect x={PAD.left} y={PAD.top} width={PW} height={PH} />
          </clipPath>
        </defs>

        {/* axes */}
        <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={PAD.top + PH} stroke="rgb(var(--border))" strokeWidth={1} />
        <line x1={PAD.left} y1={PAD.top + PH} x2={PAD.left + PW} y2={PAD.top + PH} stroke="rgb(var(--border))" strokeWidth={1} />

        {/* quadrant dividers */}
        {QUAD_TOTAL > bounds.x0 && QUAD_TOTAL < bounds.x1 && (
          <line
            x1={toX(QUAD_TOTAL)} y1={PAD.top} x2={toX(QUAD_TOTAL)} y2={PAD.top + PH}
            stroke="rgba(var(--accent-rgb,45,126,232),0.18)" strokeWidth={1} strokeDasharray="4 4"
          />
        )}
        {QUAD_COMFORT > bounds.y0 && QUAD_COMFORT < bounds.y1 && (
          <line
            x1={PAD.left} y1={toY(QUAD_COMFORT)} x2={PAD.left + PW} y2={toY(QUAD_COMFORT)}
            stroke="rgba(var(--accent-rgb,45,126,232),0.18)" strokeWidth={1} strokeDasharray="4 4"
          />
        )}
        {QUAD_TOTAL > bounds.x0 && QUAD_TOTAL < bounds.x1 && (
          <text x={toX(QUAD_TOTAL) + 6} y={PAD.top + 14} fill="rgb(var(--accent))" fontSize={9} fontFamily="monospace" opacity={0.5}>Sweet spot →</text>
        )}
        {QUAD_TOTAL > bounds.x0 && QUAD_TOTAL < bounds.x1 && QUAD_COMFORT > bounds.y0 && QUAD_COMFORT < bounds.y1 && (
          <text x={toX(QUAD_TOTAL) + 6} y={toY(QUAD_COMFORT) - 6} fill="rgb(var(--bull))" fontSize={9} fontFamily="monospace" opacity={0.5}>High comfort</text>
        )}

        {/* axis titles */}
        <text x={PAD.left + PW / 2} y={H - 8} fill="rgb(var(--dim))" fontSize={11} textAnchor="middle" fontFamily="monospace">Total Score →</text>
        <text x={14} y={PAD.top + PH / 2} fill="rgb(var(--dim))" fontSize={11} textAnchor="middle" fontFamily="monospace" transform={`rotate(-90,14,${PAD.top + PH / 2})`}>Comfort Score →</text>

        {/* x ticks */}
        {xTicks.map(v => (
          <g key={`xt-${v}`}>
            <line x1={toX(v)} y1={PAD.top + PH} x2={toX(v)} y2={PAD.top + PH + 5} stroke="rgb(var(--rim))" strokeWidth={1} />
            <text x={toX(v)} y={PAD.top + PH + 18} fill="rgb(var(--ghost))" fontSize={10} textAnchor="middle" fontFamily="monospace">{v}</text>
          </g>
        ))}

        {/* y ticks */}
        {yTicks.map(v => (
          <g key={`yt-${v}`}>
            <line x1={PAD.left - 5} y1={toY(v)} x2={PAD.left} y2={toY(v)} stroke="rgb(var(--rim))" strokeWidth={1} />
            <text x={PAD.left - 9} y={toY(v) + 4} fill="rgb(var(--ghost))" fontSize={10} textAnchor="end" fontFamily="monospace">{v}</text>
          </g>
        ))}

        {/* dots — clipped to plot area so zoom never bleeds past axes */}
        <g clipPath="url(#plot-area)">
        {plotable.map(row => {
          const cs = row.comfort_score!;
          if (row.total_score < bounds.x0 || row.total_score > bounds.x1) return null;
          if (cs < bounds.y0 || cs > bounds.y1) return null;
          const cx = toX(row.total_score);
          const cy = toY(cs);
          const r = dotRadius(row.total_score);
          const color = dotColor(row);
          const isSel = selected === row.symbol;
          const isHov = hoveredRow?.symbol === row.symbol;
          return (
            <g key={row.symbol}>
              <circle
                cx={cx} cy={cy}
                r={r + (isSel || isHov ? 3 : 0)}
                fill={color}
                fillOpacity={isSel ? 1 : isHov ? 0.85 : 0.6}
                stroke={isSel ? 'rgb(var(--fg))' : isHov ? color : color}
                strokeWidth={isSel ? 2 : isHov ? 1.5 : 1}
                strokeOpacity={0.9}
                style={{ cursor: 'pointer', transition: 'r 0.1s, fill-opacity 0.1s' }}
                onMouseEnter={() => setHoveredRow(row)}
                onMouseLeave={() => setHoveredRow(null)}
                onClick={() => {
                  if (isDraggingRef.current) return;
                  setSelected(prev => prev === row.symbol ? null : row.symbol);
                }}
              />
              {(row.total_score >= 76 || isSel || isHov) && (
                <text
                  x={cx + r + 4} y={cy + 4}
                  fill={color} fontSize={9} fontFamily="monospace" fontWeight="bold"
                  style={{ pointerEvents: 'none' }}
                >
                  {row.symbol}
                </text>
              )}
            </g>
          );
        })}
        </g>

        {scores.length > 0 && plotable.length < scores.length && (
          <text x={PAD.left + PW - 6} y={PAD.top + PH - 6} fill="rgb(var(--ghost))" fontSize={9} textAnchor="end" fontFamily="monospace">
            {scores.length - plotable.length} symbols missing comfort score hidden
          </text>
        )}
      </svg>

      {/* HTML tooltip — much more readable than SVG text */}
      {hoveredRow && (
        <div
          className="pointer-events-none absolute z-20 rounded-md border border-border bg-panel shadow-lg"
          style={{ left: ttLeft, top: ttTop, width: ttW, backdropFilter: 'blur(6px)' }}
        >
          <div className="border-b border-border/50 px-3 py-2">
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[13px] font-black text-fg">{hoveredRow.symbol}</span>
              {hoveredRow.is_fno && <span className="chip h-4 min-h-0 px-1 text-[8px]" style={{ color: 'rgb(var(--violet))' }}>F&O</span>}
              {hoveredRow.is_watchlist && <span className="chip h-4 min-h-0 px-1 text-[8px]" style={{ color: 'rgb(var(--amber))' }}>WL</span>}
              {hoveredRow.is_new_watchlist && <span className="chip h-4 min-h-0 px-1 text-[8px]" style={{ color: 'rgb(var(--accent))' }}>NEW</span>}
              <span className="ml-auto font-mono text-[10px] text-ghost">#{hoveredRow.rank}</span>
            </div>
            {hoveredRow.company_name && (
              <div className="mt-0.5 truncate font-mono text-[9px] text-ghost">{hoveredRow.company_name}</div>
            )}
          </div>
          <div className="grid grid-cols-3 gap-x-2 gap-y-1 px-3 py-2 font-mono text-[10px]">
            <span className="text-ghost">Total <span style={{ color: 'rgb(var(--accent))' }}>{hoveredRow.total_score.toFixed(0)}</span></span>
            <span className="text-ghost">Mom <span style={{ color: 'rgb(var(--amber))' }}>{hoveredRow.momentum_score.toFixed(0)}</span></span>
            <span className="text-ghost">Trend <span style={{ color: 'rgb(var(--bull))' }}>{hoveredRow.trend_score?.toFixed(0) ?? '-'}</span></span>
            <span className="text-ghost">Comfort <span style={{ color: comfortColor(hoveredRow.comfort_score) }}>{hoveredRow.comfort_score?.toFixed(0) ?? '-'}</span></span>
            <span className="text-ghost">RSI <span className="text-fg">{hoveredRow.rsi_14?.toFixed(0) ?? '-'}</span></span>
            <span className="text-ghost">ADX <span className="text-fg">{hoveredRow.adx_14?.toFixed(0) ?? '-'}</span></span>
          </div>
          <div className="border-t border-border/50 px-3 py-1.5 font-mono text-[10px]">
            <span className="text-ghost">Bias </span>
            <span style={{ color: hoveredRow.weekly_bias === 'BULLISH' ? 'rgb(var(--bull))' : hoveredRow.weekly_bias === 'BEARISH' ? 'rgb(var(--bear))' : 'rgb(var(--ghost))' }}>
              {hoveredRow.weekly_bias ?? 'NEUTRAL'}
            </span>
            {hoveredRow.comfort_interpretation && (
              <span className="ml-3 italic text-ghost">{hoveredRow.comfort_interpretation}</span>
            )}
          </div>
        </div>
      )}

      {selected && (
        <SymbolModal symbol={selected} initialTab="chart" onClose={() => setSelected(null)} />
      )}

      <div className="flex shrink-0 items-center gap-4 border-t border-border bg-panel/80 px-4 py-2 text-[10px]">
        <span className="font-black uppercase text-ghost">Legend</span>
        <LegendDot color="rgb(var(--bull))" label="Bullish" />
        <LegendDot color="rgb(var(--bear))" label="Bearish" />
        <LegendDot color="rgb(var(--amber))" label="Neutral" />
        <span className="text-ghost">· dot size = total score · scroll/buttons to zoom · drag to pan · click dot for chart</span>
        <span className="ml-auto num text-ghost">{plotable.length} plotted</span>
      </div>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <svg width={10} height={10}><circle cx={5} cy={5} r={4} fill={color} fillOpacity={0.7} /></svg>
      <span className="text-ghost">{label}</span>
    </span>
  );
}
