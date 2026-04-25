'use client';

import { memo } from 'react';
import type { TradeRow } from './accountTypes';
import { money } from './accountFmt';

const W = 600, H = 160, PL = 52, PR = 12, PT = 14, PB = 28;
const IW = W - PL - PR, IH = H - PT - PB;

export const PnLCurve = memo(function PnLCurve({ trades }: { trades: TradeRow[] }) {
  const sorted = [...trades].sort((a, b) => (a.exit_time ?? '').localeCompare(b.exit_time ?? ''));
  let running = 0;
  const pts = sorted.map(t => { running += t.pnl; return running; });

  if (!pts.length) {
    return (
      <div className="flex h-44 flex-col items-center justify-center rounded-lg border border-dashed border-border bg-panel gap-1">
        <div className="text-[22px] text-ghost/25 font-black">P&L</div>
        <div className="text-[11px] text-ghost">Cumulative curve — awaiting first trade sync</div>
      </div>
    );
  }

  const allVals = [0, ...pts];
  const min = Math.min(...allVals), max = Math.max(...allVals);
  const range = max - min || 1;
  const toY = (v: number) => PT + (1 - (v - min) / range) * IH;
  const toX = (i: number) => PL + ((i + 1) / pts.length) * IW;
  const zeroY = toY(0);
  const isPos = running >= 0;
  const color = isPos ? 'rgb(var(--bull))' : 'rgb(var(--bear))';
  const linePts = pts.map((v, i) => `${toX(i)},${toY(v)}`).join(' ');
  const fillPts = `${PL},${zeroY} ${linePts} ${toX(pts.length - 1)},${zeroY}`;
  const ticks = [min, (min + max) / 2, max].filter((v, i, a) => a.findIndex(x => Math.abs(x - v) < range * 0.05) === i);

  return (
    <div className="rounded-lg border border-border bg-panel p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-[13px] font-black text-fg">Cumulative P&L</span>
        <span className={`num text-[13px] font-black ${isPos ? 'text-bull' : 'text-bear'}`}>{money(running)}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 160 }}>
        <line x1={PL} y1={zeroY} x2={W - PR} y2={zeroY} stroke="rgb(var(--border))" strokeWidth={1} strokeDasharray="4 3" />
        <polygon points={fillPts} fill={color} fillOpacity={0.1} />
        <polyline points={linePts} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />
        {ticks.map(v => (
          <text key={v} x={PL - 4} y={toY(v) + 4} textAnchor="end" fontSize={9} fill="rgb(var(--ghost))">
            {Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(0)}k` : v.toFixed(0)}
          </text>
        ))}
        {pts.map((v, i) => (
          <circle key={i} cx={toX(i)} cy={toY(v)} r={pts.length <= 20 ? 3 : 0}
            fill={v >= 0 ? 'rgb(var(--bull))' : 'rgb(var(--bear))'}
            opacity={0.8}>
            <title>{sorted[i]?.symbol}: {money(v)} cumulative</title>
          </circle>
        ))}
      </svg>
    </div>
  );
});
PnLCurve.displayName = 'PnLCurve';
