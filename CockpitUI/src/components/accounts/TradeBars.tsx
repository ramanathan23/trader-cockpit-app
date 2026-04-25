'use client';

import { memo } from 'react';
import type { TradeRow } from './accountTypes';
import { money } from './accountFmt';

const W = 600, H = 110, PL = 8, PR = 8, PT = 10, PB = 22;
const IW = W - PL - PR, IH = H - PT - PB;
const MAX_BARS = 180;

export const TradeBars = memo(function TradeBars({ trades }: { trades: TradeRow[] }) {
  if (!trades.length) {
    return (
      <div className="flex h-28 items-center justify-center rounded-lg border border-dashed border-border bg-panel">
        <span className="text-[11px] text-ghost">Trade P&L bars — awaiting first trade sync</span>
      </div>
    );
  }

  const totalTrades = trades.length;
  const sorted = [...trades]
    .sort((a, b) => (a.exit_time ?? '').localeCompare(b.exit_time ?? ''))
    .slice(-MAX_BARS);
  const maxAbs = Math.max(1, ...sorted.map(t => Math.abs(t.pnl)));
  const midY = PT + IH / 2;
  const halfH = IH / 2 - 2;
  const barW = Math.max(2, Math.min(18, IW / sorted.length - 2));
  const gap = IW / sorted.length;
  const wins = sorted.filter(t => t.pnl > 0).length;
  const losses = sorted.filter(t => t.pnl < 0).length;

  return (
    <div className="rounded-lg border border-border bg-panel p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-[13px] font-black text-fg">Trade-by-Trade P&L</span>
        <span className="text-[11px] text-ghost">
          <span className="text-bull font-black">{wins}W</span>
          <span className="mx-1 text-ghost">/</span>
          <span className="text-bear font-black">{losses}L</span>
          <span className="ml-2">{sorted.length}/{totalTrades} shown</span>
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 110 }}>
        <line x1={PL} y1={midY} x2={W - PR} y2={midY} stroke="rgb(var(--border))" strokeWidth={1} />
        {sorted.map((t, i) => {
          const x = PL + i * gap + (gap - barW) / 2;
          const h = Math.max(2, (Math.abs(t.pnl) / maxAbs) * halfH);
          const y = t.pnl >= 0 ? midY - h : midY;
          const isWin = t.pnl >= 0;
          return (
            <rect key={i} x={x} y={y} width={barW} height={h} rx={1}
              fill={isWin ? 'rgb(var(--bull))' : 'rgb(var(--bear))'} fillOpacity={0.75}>
              <title>{t.symbol} {t.exit_time?.slice(0, 10)}: {money(t.pnl)}</title>
            </rect>
          );
        })}
        <text x={PL} y={H - 6} fontSize={8} fill="rgb(var(--ghost))">oldest</text>
        <text x={W - PR} y={H - 6} fontSize={8} textAnchor="end" fill="rgb(var(--ghost))">latest</text>
      </svg>
    </div>
  );
});
TradeBars.displayName = 'TradeBars';
