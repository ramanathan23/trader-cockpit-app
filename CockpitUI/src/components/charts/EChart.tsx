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
    chartRef.current?.setOption(option, true);
  }, [option]);

  return <div ref={hostRef} className={className} style={style} />;
});
EChart.displayName = 'EChart';

