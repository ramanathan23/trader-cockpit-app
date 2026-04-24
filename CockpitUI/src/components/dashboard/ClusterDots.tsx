'use client';

import { memo } from 'react';
import type { ScoredSymbol } from '@/domain/dashboard';
import { dotColor, dotRadius, PAD, PW, PH } from '@/lib/clusterUtils';
import type { ViewBounds } from '@/lib/clusterUtils';

interface ClusterDotsProps {
  plotable: ScoredSymbol[];
  scores:   ScoredSymbol[];
  bounds:   ViewBounds;
  toX: (v: number) => number;
  toY: (v: number) => number;
  hoveredRow:    ScoredSymbol | null;
  setHoveredRow: (row: ScoredSymbol | null) => void;
  selected:    string | null;
  setSelected: (sym: string | null) => void;
  isDraggingRef: React.MutableRefObject<boolean>;
}

export const ClusterDots = memo(({ plotable, scores, bounds, toX, toY, hoveredRow, setHoveredRow, selected, setSelected, isDraggingRef }: ClusterDotsProps) => (
  <>
    <defs>
      <clipPath id="plot-area">
        <rect x={PAD.left} y={PAD.top} width={PW} height={PH} />
      </clipPath>
    </defs>
    <g clipPath="url(#plot-area)">
      {plotable.map(row => {
        const cs = row.comfort_score!;
        if (row.total_score < bounds.x0 || row.total_score > bounds.x1) return null;
        if (cs < bounds.y0 || cs > bounds.y1) return null;
        const cx    = toX(row.total_score);
        const cy    = toY(cs);
        const r     = dotRadius(row.total_score);
        const color = dotColor(row);
        const isSel = selected === row.symbol;
        const isHov = hoveredRow?.symbol === row.symbol;
        return (
          <g key={row.symbol}>
            <circle cx={cx} cy={cy} r={r + (isSel || isHov ? 3 : 0)}
              fill={color} fillOpacity={isSel ? 1 : isHov ? 0.85 : 0.6}
              stroke={color} strokeWidth={isSel ? 2 : isHov ? 1.5 : 1} strokeOpacity={0.9}
              style={{ cursor: 'pointer', transition: 'r 0.1s, fill-opacity 0.1s' }}
              onMouseEnter={() => setHoveredRow(row)}
              onMouseLeave={() => setHoveredRow(null)}
              onClick={() => { if (isDraggingRef.current) return; setSelected(selected === row.symbol ? null : row.symbol); }}
            />
            {(row.total_score >= 76 || isSel || isHov) && (
              <text x={cx + r + 4} y={cy + 4} fill={color} fontSize={9} fontFamily="monospace" fontWeight="bold"
                style={{ pointerEvents: 'none' }}>
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
  </>
));
ClusterDots.displayName = 'ClusterDots';
