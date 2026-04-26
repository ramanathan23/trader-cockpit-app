'use client';

import { memo, useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';

interface EChartProps {
  option: EChartsOption;
  className?: string;
  style?: React.CSSProperties;
  onClick?: (params: unknown) => void;
}

export const EChart = memo(function EChart({ option, className, style, onClick }: EChartProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const clickRef = useRef(onClick);

  useEffect(() => {
    clickRef.current = onClick;
  }, [onClick]);

  useEffect(() => {
    if (!hostRef.current) return;

    const chart = echarts.init(hostRef.current, undefined, { renderer: 'canvas' });
    chartRef.current = chart;

    const resize = () => chart.resize();
    const observer = new ResizeObserver(resize);
    observer.observe(hostRef.current);
    window.addEventListener('resize', resize);

    const handleClick = (params: unknown) => clickRef.current?.(params);
    chart.on('click', handleClick);

    return () => {
      chart.off('click', handleClick);
      observer.disconnect();
      window.removeEventListener('resize', resize);
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(withoutHoverFade(option), true);
  }, [option]);

  return <div ref={hostRef} className={className} style={style} />;
});
EChart.displayName = 'EChart';

function withoutHoverFade(option: EChartsOption): EChartsOption {
  const next = { ...option } as EChartsOption & { series?: unknown };
  if (!next.series) return next;
  const series = Array.isArray(next.series) ? next.series : [next.series];
  next.series = series.map(item => {
    if (!item || typeof item !== 'object') return item;
    return {
      ...(item as Record<string, unknown>),
      emphasis: { disabled: true },
      blur: { itemStyle: { opacity: 1 }, label: { opacity: 1 } },
    };
  });
  return next;
}
