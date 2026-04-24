'use client';

import { memo } from 'react';
import { PAD, PW, PH, W, H, QUAD_TOTAL, QUAD_COMFORT } from '@/lib/clusterUtils';
import type { ViewBounds } from '@/lib/clusterUtils';

interface ClusterBackgroundProps {
  bounds: ViewBounds;
  xTicks: number[];
  yTicks: number[];
  toX: (v: number) => number;
  toY: (v: number) => number;
}

export const ClusterBackground = memo(({ bounds, xTicks, yTicks, toX, toY }: ClusterBackgroundProps) => (
  <>
    <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={PAD.top + PH} stroke="rgb(var(--border))" strokeWidth={1} />
    <line x1={PAD.left} y1={PAD.top + PH} x2={PAD.left + PW} y2={PAD.top + PH} stroke="rgb(var(--border))" strokeWidth={1} />

    <text x={PAD.left + PW / 2} y={H - 8} fill="rgb(var(--dim))" fontSize={11} textAnchor="middle" fontFamily="monospace">Total Score →</text>
    <text x={14} y={PAD.top + PH / 2} fill="rgb(var(--dim))" fontSize={11} textAnchor="middle" fontFamily="monospace"
      transform={`rotate(-90,14,${PAD.top + PH / 2})`}>Comfort Score →</text>

    {QUAD_TOTAL > bounds.x0 && QUAD_TOTAL < bounds.x1 && (
      <line x1={toX(QUAD_TOTAL)} y1={PAD.top} x2={toX(QUAD_TOTAL)} y2={PAD.top + PH}
        stroke="rgba(var(--accent-rgb,45,126,232),0.18)" strokeWidth={1} strokeDasharray="4 4" />
    )}
    {QUAD_COMFORT > bounds.y0 && QUAD_COMFORT < bounds.y1 && (
      <line x1={PAD.left} y1={toY(QUAD_COMFORT)} x2={PAD.left + PW} y2={toY(QUAD_COMFORT)}
        stroke="rgba(var(--accent-rgb,45,126,232),0.18)" strokeWidth={1} strokeDasharray="4 4" />
    )}
    {QUAD_TOTAL > bounds.x0 && QUAD_TOTAL < bounds.x1 && (
      <text x={toX(QUAD_TOTAL) + 6} y={PAD.top + 14} fill="rgb(var(--accent))" fontSize={9} fontFamily="monospace" opacity={0.5}>Sweet spot →</text>
    )}
    {QUAD_TOTAL > bounds.x0 && QUAD_TOTAL < bounds.x1 && QUAD_COMFORT > bounds.y0 && QUAD_COMFORT < bounds.y1 && (
      <text x={toX(QUAD_TOTAL) + 6} y={toY(QUAD_COMFORT) - 6} fill="rgb(var(--bull))" fontSize={9} fontFamily="monospace" opacity={0.5}>High comfort</text>
    )}

    {xTicks.map(v => (
      <g key={`xt-${v}`}>
        <line x1={toX(v)} y1={PAD.top + PH} x2={toX(v)} y2={PAD.top + PH + 5} stroke="rgb(var(--rim))" strokeWidth={1} />
        <text x={toX(v)} y={PAD.top + PH + 18} fill="rgb(var(--ghost))" fontSize={10} textAnchor="middle" fontFamily="monospace">{v}</text>
      </g>
    ))}
    {yTicks.map(v => (
      <g key={`yt-${v}`}>
        <line x1={PAD.left - 5} y1={toY(v)} x2={PAD.left} y2={toY(v)} stroke="rgb(var(--rim))" strokeWidth={1} />
        <text x={PAD.left - 9} y={toY(v) + 4} fill="rgb(var(--ghost))" fontSize={10} textAnchor="end" fontFamily="monospace">{v}</text>
      </g>
    ))}
  </>
));
ClusterBackground.displayName = 'ClusterBackground';
