'use client';

import { memo, useMemo } from 'react';
import type { ScoredSymbol } from '@/domain/dashboard';
import type { StockRow } from '@/domain/stocklist';
import { ClusterChart } from '@/components/dashboard/ClusterChart';

interface StockListClusterViewProps {
  rows:    StockRow[];
  loading: boolean;
}

export const StockListClusterView = memo(({ rows, loading }: StockListClusterViewProps) => {
  const scored = useMemo(
    () => rows.filter(r => r.total_score != null && r.comfort_score != null) as unknown as ScoredSymbol[],
    [rows],
  );

  if (!loading && scored.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-[13px] text-ghost">
        No scored stocks — run scoring pipeline first.
      </div>
    );
  }

  return <ClusterChart scores={scored} loading={loading} />;
});
StockListClusterView.displayName = 'StockListClusterView';
