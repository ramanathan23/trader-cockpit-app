'use client';

import { memo, useCallback, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { cn } from '@/lib/cn';
import { fmt2 } from '@/lib/fmt';
import { rsiColor } from '@/lib/scoreColors';
import { screenerF52hColor, screenerPctText, screenerStageColor, screenerStageLabel } from '@/lib/screenerDisplay';
import { setupTier, TIER_TEXT_CLASS, TIER_LABEL } from '@/lib/setupTier';
import { DailyChart } from '@/components/dashboard/DailyChart';
import type { StockRow } from '@/domain/stocklist';
import type { LivePriceData } from '@/components/ui/LivePrice';

interface ChartRowProps {
  row:      StockRow;
  selected: boolean;
  livePrice?: LivePriceData;
  onSelect: () => void;
}

const ChartRow = memo(({ row, selected, livePrice, onSelect }: ChartRowProps) => {
  const tier  = setupTier(row);
  const price = livePrice?.ltp ?? row.display_price;
  return (
    <div
      className={cn('flex cursor-pointer items-center gap-2 border-b border-border/40 px-3 py-2 transition-colors hover:bg-lift/40',
        selected && 'bg-accent/10 border-l-2 border-accent',
        !selected && tier && TIER_TEXT_CLASS[tier] && 'border-l-[2px]',
      )}
      style={!selected && tier ? { borderLeftColor: `var(--${tier === 'STRONG' ? 'bull' : tier === 'BUILDING' ? 'accent' : 'amber'})` } : undefined}
      onClick={onSelect}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="text-[13px] font-black text-fg">{row.symbol}</span>
          {tier && <span className={cn('text-[9px] font-black', TIER_TEXT_CLASS[tier])}>{TIER_LABEL[tier]}</span>}
        </div>
        <div className="flex items-center gap-2 text-[10px] text-ghost">
          <span style={{ color: screenerStageColor(row.stage) }}>{screenerStageLabel(row.stage)}</span>
          {row.rsi_14 != null && <span style={{ color: rsiColor(row.rsi_14) }}>RSI {row.rsi_14.toFixed(0)}</span>}
          {row.f52h   != null && <span style={{ color: screenerF52hColor(row.f52h) }}>{screenerPctText(row.f52h, true)}</span>}
        </div>
      </div>
      <div className="shrink-0 text-right">
        {row.total_score != null && (
          <div className="num text-[14px] font-black text-fg">{row.total_score.toFixed(0)}</div>
        )}
        {price != null && <div className="num text-[10px] text-ghost">{fmt2(price)}</div>}
      </div>
    </div>
  );
});
ChartRow.displayName = 'ChartRow';

interface StockListChartViewProps {
  rows:       StockRow[];
  livePrices: Record<string, LivePriceData>;
  loading?:   boolean;
  hasMore?:   boolean;
  onLoadMore?: () => void;
}

export const StockListChartView = memo(({ rows, livePrices, loading, hasMore, onLoadMore }: StockListChartViewProps) => {
  const [selected, setSelected] = useState<string | null>(rows[0]?.symbol ?? null);
  const activeSymbol = selected ?? rows[0]?.symbol;
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 58,
    overscan: 12,
  });

  const handleScroll = useCallback(() => {
    const el = parentRef.current;
    if (!el || loading || !hasMore || !onLoadMore) return;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 260) onLoadMore();
  }, [loading, hasMore, onLoadMore]);

  return (
    <div className="flex min-h-0 flex-1">
      <div ref={parentRef} className="w-[340px] shrink-0 overflow-y-auto border-r border-border" onScroll={handleScroll}>
        <div className="relative" style={{ height: virtualizer.getTotalSize() }}>
          {virtualizer.getVirtualItems().map(item => {
            const row = rows[item.index];
            return (
              <div key={row.symbol} className="absolute left-0 top-0 w-full" style={{ transform: `translateY(${item.start}px)` }}>
                <ChartRow row={row} livePrice={livePrices[row.symbol]}
                  selected={activeSymbol === row.symbol} onSelect={() => setSelected(row.symbol)} />
              </div>
            );
          })}
        </div>
        {rows.length === 0 && (
          <div className="py-12 text-center text-[12px] text-ghost">No stocks</div>
        )}
      </div>
      <div className="flex min-h-0 flex-1 flex-col">
        {activeSymbol
          ? <DailyChart symbol={activeSymbol} height="100%" />
          : <div className="flex flex-1 items-center justify-center text-[13px] text-ghost">Select a stock</div>
        }
      </div>
    </div>
  );
});
StockListChartView.displayName = 'StockListChartView';
