'use client';

import { useState, useRef, useCallback } from 'react';
import type { ScoredSymbol } from '@/domain/dashboard';
import { SymbolModal } from './SymbolModal';

// ─── layout constants ───────────────────────────────────────────────────────
const W = 900;
const H = 540;
const PAD = { top: 32, right: 28, bottom: 52, left: 56 };
const PW = W - PAD.left - PAD.right;
const PH = H - PAD.top - PAD.bottom;

// ─── helpers ─────────────────────────────────────────────────────────────────
function toX(totalScore: number) {
  return PAD.left + (totalScore / 100) * PW;
}
function toY(comfort: number) {
  return PAD.top + (1 - comfort / 100) * PH;
}

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

// ─── component ───────────────────────────────────────────────────────────────
interface TooltipData {
  row: ScoredSymbol;
  svgX: number;
  svgY: number;
}

interface ClusterChartProps {
  scores: ScoredSymbol[];
  loading: boolean;
}

export function ClusterChart({ scores, loading }: ClusterChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  const handleEnter = useCallback((row: ScoredSymbol, e: React.MouseEvent<SVGCircleElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const scaleX = W / rect.width;
    const scaleY = H / rect.height;
    setTooltip({
      row,
      svgX: (e.clientX - rect.left) * scaleX,
      svgY: (e.clientY - rect.top) * scaleY,
    });
  }, []);

  const handleMove = useCallback((row: ScoredSymbol, e: React.MouseEvent<SVGCircleElement>) => {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const scaleX = W / rect.width;
    const scaleY = H / rect.height;
    setTooltip(prev =>
      prev?.row.symbol === row.symbol
        ? { ...prev, svgX: (e.clientX - rect.left) * scaleX, svgY: (e.clientY - rect.top) * scaleY }
        : prev,
    );
  }, []);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center text-[13px] text-dim">
        Computing cluster…
      </div>
    );
  }

  const plotable = scores.filter(s => s.comfort_score != null);
  const axisX = PAD.left + PW / 2;
  const axisY = PAD.top + PH / 2;

  // tooltip position — keep inside viewBox
  const ttW = 220;
  const ttH = 110;
  const ttX = tooltip
    ? Math.min(tooltip.svgX + 16, W - ttW - 8)
    : 0;
  const ttY = tooltip
    ? Math.max(tooltip.svgY - ttH / 2, PAD.top)
    : 0;

  return (
    <div className="relative flex flex-1 flex-col overflow-hidden">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="h-full w-full"
        style={{ userSelect: 'none' }}
        onMouseLeave={() => setTooltip(null)}
      >
        {/* ── axes ── */}
        <line
          x1={PAD.left} y1={PAD.top}
          x2={PAD.left} y2={PAD.top + PH}
          stroke="rgb(var(--border))" strokeWidth={1}
        />
        <line
          x1={PAD.left} y1={PAD.top + PH}
          x2={PAD.left + PW} y2={PAD.top + PH}
          stroke="rgb(var(--border))" strokeWidth={1}
        />

        {/* ── quadrant dividers removed ── */}

        {/* ── axis title ── */}
        <text
          x={axisX} y={H - 8}
          fill="rgb(var(--dim))" fontSize={11} textAnchor="middle" fontFamily="monospace"
        >
          Total Score →
        </text>
        <text
          x={14} y={axisY}
          fill="rgb(var(--dim))" fontSize={11} textAnchor="middle" fontFamily="monospace"
          transform={`rotate(-90, 14, ${axisY})`}
        >
          Comfort Score →
        </text>

        {/* ── x-axis ticks ── */}
        {[0, 25, 50, 75, 100].map(v => (
          <g key={`xt-${v}`}>
            <line
              x1={toX(v)} y1={PAD.top + PH}
              x2={toX(v)} y2={PAD.top + PH + 5}
              stroke="rgb(var(--rim))" strokeWidth={1}
            />
            <text
              x={toX(v)} y={PAD.top + PH + 18}
              fill="rgb(var(--ghost))" fontSize={10} textAnchor="middle" fontFamily="monospace"
            >
              {v}
            </text>
          </g>
        ))}

        {/* ── y-axis ticks ── */}
        {[0, 25, 50, 75, 100].map(v => (
          <g key={`yt-${v}`}>
            <line
              x1={PAD.left - 5} y1={toY(v)}
              x2={PAD.left} y2={toY(v)}
              stroke="rgb(var(--rim))" strokeWidth={1}
            />
            <text
              x={PAD.left - 9} y={toY(v) + 4}
              fill="rgb(var(--ghost))" fontSize={10} textAnchor="end" fontFamily="monospace"
            >
              {v}
            </text>
          </g>
        ))}

        {/* ── dots ── */}
        {plotable.map(row => {
          const cx = toX(row.total_score);
          const cy = toY(row.comfort_score!);
          const r = dotRadius(row.total_score);
          const color = dotColor(row);
          const isSel = selected === row.symbol;
          const isHov = tooltip?.row.symbol === row.symbol;
          return (
            <g key={row.symbol}>
              <circle
                cx={cx} cy={cy}
                r={r + (isSel || isHov ? 3 : 0)}
                fill={color}
                fillOpacity={isSel ? 1 : 0.6}
                stroke={isSel ? 'rgb(var(--fg))' : color}
                strokeWidth={isSel ? 2 : 1}
                strokeOpacity={0.9}
                style={{ cursor: 'pointer', transition: 'r 0.1s' }}
                onMouseEnter={e => handleEnter(row, e)}
                onMouseMove={e => handleMove(row, e)}
                onMouseLeave={() => setTooltip(null)}
                onClick={() => setSelected(prev => (prev === row.symbol ? null : row.symbol))}
              />
              {/* label: top scorers + selected */}
              {(row.total_score >= 78 || isSel) && (
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

        {/* ── no-comfort notice ── */}
        {scores.length > 0 && plotable.length < scores.length && (
          <text
            x={PAD.left + PW - 6} y={PAD.top + PH - 6}
            fill="rgb(var(--ghost))" fontSize={9} textAnchor="end" fontFamily="monospace"
          >
            {scores.length - plotable.length} symbols missing comfort score hidden
          </text>
        )}

        {/* ── tooltip ── */}
        {tooltip && (
          <g>
            <rect
              x={ttX} y={ttY}
              width={ttW} height={ttH}
              rx={6}
              fill="rgb(var(--panel))" fillOpacity={0.97}
              stroke="rgb(var(--border))" strokeWidth={1}
            />
            {/* symbol row */}
            <text x={ttX + 10} y={ttY + 20} fill="rgb(var(--fg))" fontSize={12} fontFamily="monospace" fontWeight="bold">
              {tooltip.row.symbol}
            </text>
            {tooltip.row.is_fno && (
              <text x={ttX + 10 + tooltip.row.symbol.length * 7.5} y={ttY + 20} fill="rgb(var(--violet))" fontSize={9} fontFamily="monospace">
                {' '}F&amp;O
              </text>
            )}
            {tooltip.row.is_watchlist && (
              <text x={ttX + 10 + tooltip.row.symbol.length * 7.5 + (tooltip.row.is_fno ? 28 : 0)} y={ttY + 20} fill="rgb(var(--amber))" fontSize={9} fontFamily="monospace">
                {' '}WL
              </text>
            )}
            {/* company */}
            {tooltip.row.company_name && (
              <text x={ttX + 10} y={ttY + 34} fill="rgb(var(--ghost))" fontSize={9} fontFamily="monospace">
                {tooltip.row.company_name.slice(0, 28)}
              </text>
            )}
            {/* scores */}
            <text x={ttX + 10} y={ttY + 54} fill="rgb(var(--ghost))" fontSize={10} fontFamily="monospace">
              {'Mom '}
              <tspan fill="rgb(var(--amber))">{tooltip.row.momentum_score.toFixed(0)}</tspan>
              {'   Comfort '}
              <tspan fill={comfortColor(tooltip.row.comfort_score)}>
                {tooltip.row.comfort_score?.toFixed(0) ?? '-'}
              </tspan>
            </text>
            <text x={ttX + 10} y={ttY + 70} fill="rgb(var(--ghost))" fontSize={10} fontFamily="monospace">
              {'Total '}
              <tspan fill="rgb(var(--accent))">{tooltip.row.total_score.toFixed(0)}</tspan>
              {'   Rank '}
              <tspan fill="rgb(var(--fg))">#{tooltip.row.rank}</tspan>
            </text>
            {tooltip.row.rsi_14 != null && (
              <text x={ttX + 10} y={ttY + 86} fill="rgb(var(--ghost))" fontSize={10} fontFamily="monospace">
                {'RSI '}
                <tspan fill="rgb(var(--fg))">{tooltip.row.rsi_14.toFixed(0)}</tspan>
                {tooltip.row.weekly_bias ? '   Bias ' : ''}
                {tooltip.row.weekly_bias && (
                  <tspan fill={
                    tooltip.row.weekly_bias === 'BULLISH' ? 'rgb(var(--bull))'
                      : tooltip.row.weekly_bias === 'BEARISH' ? 'rgb(var(--bear))'
                      : 'rgb(var(--ghost))'
                  }>
                    {tooltip.row.weekly_bias.slice(0, 4)}
                  </tspan>
                )}
              </text>
            )}
          </g>
        )}
      </svg>

      {/* ── selected symbol modal ── */}
      {selected && (
        <SymbolModal symbol={selected} initialTab="chart" onClose={() => setSelected(null)} />
      )}

      {/* ── legend ── */}
      <div className="flex shrink-0 items-center gap-4 border-t border-border bg-panel/80 px-4 py-2 text-[10px]">
        <span className="font-black uppercase text-ghost">Legend</span>
        <LegendDot color="rgb(var(--bull))" label="Bullish" />
        <LegendDot color="rgb(var(--bear))" label="Bearish" />
        <LegendDot color="rgb(var(--amber))" label="Neutral" />
        <span className="text-ghost">· dot size = total score · click dot for chart</span>
        <span className="ml-auto num text-ghost">{plotable.length} symbols plotted</span>
      </div>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <svg width={10} height={10}>
        <circle cx={5} cy={5} r={4} fill={color} fillOpacity={0.7} />
      </svg>
      <span className="text-ghost">{label}</span>
    </span>
  );
}
