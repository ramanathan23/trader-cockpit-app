'use client';

import { memo, useEffect, useRef, useState } from 'react';
import { createChart, CandlestickSeries, LineSeries, type IChartApi, type CandlestickData, type Time } from 'lightweight-charts';
import type { OHLCBar } from '@/domain/chart';

interface DailyChartProps {
  symbol: string;
  height?: number;
}

function computeEMA(bars: OHLCBar[], period: number): { time: string; value: number }[] {
  if (bars.length < period) return [];
  const k = 2 / (period + 1);
  const seed = bars.slice(0, period).reduce((s, b) => s + b.close, 0) / period;
  const result: { time: string; value: number }[] = [];
  let ema = seed;
  for (let i = period - 1; i < bars.length; i++) {
    if (i > period - 1) ema = bars[i].close * k + ema * (1 - k);
    result.push({ time: bars[i].time, value: ema });
  }
  return result;
}

export const DailyChart = memo(({ symbol, height = 300 }: DailyChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef     = useRef<IChartApi | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { color: 'transparent' },
        textColor: 'rgb(116, 142, 170)',
        fontSize: 10,
      },
      grid: {
        vertLines: { color: 'rgba(60, 80, 110, 0.35)' },
        horzLines: { color: 'rgba(60, 80, 110, 0.35)' },
      },
      crosshair: {
        vertLine: { color: 'rgba(45, 126, 232, 0.3)', width: 1, style: 2 },
        horzLine: { color: 'rgba(45, 126, 232, 0.3)', width: 1, style: 2 },
      },
      timeScale: {
        borderColor: 'rgba(40, 55, 80, 0.8)',
        timeVisible: false,
      },
      rightPriceScale: {
        borderColor: 'rgba(40, 55, 80, 0.8)',
      },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor:       '#0dbd7d',
      downColor:     '#f23d55',
      borderUpColor: '#0dbd7d',
      borderDownColor: '#f23d55',
      wickUpColor:   '#0dbd7d',
      wickDownColor: '#f23d55',
    });

    const ema50Series = chart.addSeries(LineSeries, {
      color:              '#e8933a',
      lineWidth:          1,
      priceLineVisible:   false,
      lastValueVisible:   false,
      crosshairMarkerVisible: false,
    });

    const ema200Series = chart.addSeries(LineSeries, {
      color:              '#9b72f7',
      lineWidth:          1,
      priceLineVisible:   false,
      lastValueVisible:   false,
      crosshairMarkerVisible: false,
    });

    chartRef.current = chart;

    // Fetch data
    fetch(`/api/v1/chart/${encodeURIComponent(symbol)}/daily`)
      .then(r => {
        if (!r.ok) throw new Error(`${r.status}`);
        return r.json();
      })
      .then((res: { candles: OHLCBar[] } | OHLCBar[]) => {
        const bars: OHLCBar[] = Array.isArray(res) ? res : res.candles;
        const data: CandlestickData<Time>[] = bars.map(b => ({
          time:  b.time as Time,
          open:  b.open,
          high:  b.high,
          low:   b.low,
          close: b.close,
        }));
        series.setData(data);

        const ema50  = computeEMA(bars, 50).map(p => ({ time: p.time as Time, value: p.value }));
        const ema200 = computeEMA(bars, 200).map(p => ({ time: p.time as Time, value: p.value }));
        if (ema50.length)  ema50Series.setData(ema50);
        if (ema200.length) ema200Series.setData(ema200);

        chart.timeScale().fitContent();
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });

    const ro = new ResizeObserver(entries => {
      const { width } = entries[0].contentRect;
      chart.applyOptions({ width });
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [symbol, height]);

  return (
    <div className="relative">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center text-[10px] text-ghost z-10">
          Loading chart…
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center text-[10px] text-bear z-10">
          Chart error: {error}
        </div>
      )}
      <div ref={containerRef} style={{ width: '100%', height }} />
    </div>
  );
});

DailyChart.displayName = 'DailyChart';
