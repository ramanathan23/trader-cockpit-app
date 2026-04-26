'use client';

import type { Signal } from '@/domain/signal';
import type { StockRow } from '@/domain/stocklist';
import type { LivePriceData } from '@/components/ui/LivePrice';
import { fmt2 } from '@/lib/fmt';
import { computeChgPct, latestSignalLabel } from './overviewUtils';

export function TopSetups({
  rows, livePrices, signals, onSymbol,
}: {
  rows: StockRow[];
  livePrices: Record<string, LivePriceData>;
  signals: Signal[];
  onSymbol: (symbol: string) => void;
}) {
  return (
    <div className="grid gap-2 p-3 md:grid-cols-2 xl:grid-cols-4">
      {rows.map(row => (
        <SetupCard
          key={row.symbol}
          row={row}
          livePrice={livePrices[row.symbol]}
          signals={signals}
          onSymbol={onSymbol}
        />
      ))}
    </div>
  );
}

function SetupCard({
  row, livePrice, signals, onSymbol,
}: { row: StockRow; livePrice?: LivePriceData; signals: Signal[]; onSymbol: (symbol: string) => void }) {
  const chg = computeChgPct(livePrice, row);
  const tone = chg == null ? 'text-ghost' : chg >= 0 ? 'text-bull' : 'text-bear';
  return (
    <button type="button" onClick={() => onSymbol(row.symbol)}
      className="min-w-0 rounded border border-border bg-base/60 p-3 text-left transition-colors hover:border-rim hover:bg-lift/55">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-[13px] font-black text-fg">{row.symbol}</div>
          <div className="mt-0.5 truncate text-[10px] text-ghost">{row.stage ?? row.weekly_bias ?? 'Unstaged'}</div>
        </div>
        <div className="num text-right text-[16px] font-black text-accent">{fmt2(row.total_score)}</div>
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2 text-[10px]">
        <SmallStat label="Mom" value={fmt2(row.momentum_score)} />
        <SmallStat label="Trend" value={fmt2(row.trend_score)} />
        <SmallStat label="RSI" value={fmt2(row.rsi_14)} />
        <SmallStat label="Day" value={chg == null ? '-' : `${chg > 0 ? '+' : ''}${chg.toFixed(2)}%`} tone={tone} />
      </div>
      <div className="mt-2 flex items-center justify-between text-[10px] text-ghost">
        <span>{latestSignalLabel(signals, row.symbol) ?? 'No live signal'}</span>
        {row.is_fno && <span className="font-black text-violet">F&O</span>}
      </div>
    </button>
  );
}

function SmallStat({ label, value, tone = 'text-dim' }: { label: string; value: string; tone?: string }) {
  return (
    <span>
      <span className="block text-ghost">{label}</span>
      <span className={`num block font-black ${tone}`}>{value}</span>
    </span>
  );
}
