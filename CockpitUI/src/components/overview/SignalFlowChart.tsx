'use client';

import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { Signal, SignalType } from '@/domain/signal';
import { signalShort } from '@/domain/signal';
import { EChart } from '@/components/charts/EChart';
import { useEChartColors } from '@/components/charts/useEChartColors';

export function SignalFlowChart({
  signals, metricsCache, expanded = false,
}: { signals: Signal[]; metricsCache: Record<string, InstrumentMetrics | null>; expanded?: boolean }) {
  const colors = useEChartColors();
  const entries = useMemo(() => {
    const counts = new Map<SignalType, number>();
    for (const signal of signals) counts.set(signal.signal_type, (counts.get(signal.signal_type) ?? 0) + 1);
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [signals]);
  const option = useMemo<EChartsOption>(() => ({
    backgroundColor: 'transparent',
    grid: { left: 72, right: 14, top: 18, bottom: 24 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, borderColor: colors.border, backgroundColor: colors.panel, textStyle: { color: colors.fg } },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: colors.border, opacity: 0.55 } }, axisLabel: { color: colors.ghost } },
    yAxis: {
      type: 'category',
      data: entries.map(([type]) => signalShort(type)),
      axisLabel: { color: colors.ghost, fontSize: 10 },
      axisLine: { lineStyle: { color: colors.border } },
      axisTick: { show: false },
    },
    series: [{ type: 'bar', barMaxWidth: 18, data: entries.map(([type, value]) => ({ value, itemStyle: { color: type.includes('BREAK') ? colors.accent : colors.violet } })) }],
  }), [colors, entries]);
  const fnoSignals = signals.filter(signal => metricsCache[signal.symbol]?.is_fno).length;
  return (
    <div className={expanded ? 'flex min-h-0 h-full w-full flex-col' : undefined}>
      <EChart option={option} className={expanded ? 'min-h-0 flex-1 w-full' : 'h-52 w-full'} />
      <div className="border-t border-border px-3 py-2 text-[10px] text-ghost">
        <span className="num text-accent">{signals.length}</span> live signals, <span className="num text-violet">{fnoSignals}</span> F&O
      </div>
    </div>
  );
}
