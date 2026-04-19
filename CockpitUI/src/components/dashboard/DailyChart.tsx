'use client';

import { memo, useEffect, useRef, useState, useCallback } from 'react';
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type CandlestickData,
  type HistogramData,
  type Time,
} from 'lightweight-charts';
import type { OHLCBar } from '@/domain/chart';

interface DailyChartProps {
  symbol: string;
  height?: number | string;
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

/** Build volume profile — horizontal histogram of volume at price levels. */
function buildVolumeProfile(
  bars: OHLCBar[],
  buckets: number = 24,
): { price: number; vol: number; pct: number }[] {
  if (bars.length === 0) return [];
  const lo = Math.min(...bars.map(b => b.low));
  const hi = Math.max(...bars.map(b => b.high));
  if (hi === lo) return [];
  const step = (hi - lo) / buckets;
  const profile: number[] = new Array(buckets).fill(0);

  for (const b of bars) {
    // Distribute bar volume across price buckets it touches
    const bLo = Math.max(0, Math.floor((b.low - lo) / step));
    const bHi = Math.min(buckets - 1, Math.floor((b.high - lo) / step));
    const spread = bHi - bLo + 1;
    for (let i = bLo; i <= bHi; i++) {
      profile[i] += b.volume / spread;
    }
  }
  const maxVol = Math.max(...profile);
  return profile.map((vol, i) => ({
    price: lo + (i + 0.5) * step,
    vol,
    pct: maxVol > 0 ? vol / maxVol : 0,
  }));
}

/** Legend state for crosshair hover. */
interface LegendData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema50?: number;
  ema200?: number;
}

export const DailyChart = memo(({ symbol, height = 300 }: DailyChartProps) => {
  const containerRef    = useRef<HTMLDivElement>(null);
  const vpCanvasRef     = useRef<HTMLCanvasElement>(null);
  const chartRef        = useRef<IChartApi | null>(null);
  const profileRef      = useRef<{ price: number; vol: number; pct: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);
  const [legend,  setLegend]  = useState<LegendData | null>(null);

  // Volume profile draw callback — called after data loads and on resize
  const drawVolumeProfile = useCallback(
    (profile: { price: number; vol: number; pct: number }[], series: { priceToCoordinate: (price: number) => number | null }) => {
      const canvas = vpCanvasRef.current;
      if (!canvas || profile.length === 0) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width  = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, rect.width, rect.height);

      const maxBarW = rect.width * 0.15; // VP bars max 15% of chart width

      for (const row of profile) {
        const y = series.priceToCoordinate(row.price);
        if (y == null) continue;
        const barW = row.pct * maxBarW;
        const barH = Math.max(1, rect.height / profile.length - 1);
        ctx.fillStyle = row.pct > 0.7
          ? 'rgba(147, 130, 220, 0.35)'
          : 'rgba(147, 130, 220, 0.15)';
        // Draw from right edge inward
        ctx.fillRect(rect.width - barW, y - barH / 2, barW, barH);
      }
    },
    [],
  );

  useEffect(() => {
    if (!containerRef.current) return;

    const initHeight = containerRef.current.offsetHeight || (typeof height === 'number' ? height : 400);

    const chart = createChart(containerRef.current, {
      height: initHeight,
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

    // ── Candlestick series ──
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor:       '#0dbd7d',
      downColor:     '#f23d55',
      borderUpColor: '#0dbd7d',
      borderDownColor: '#f23d55',
      wickUpColor:   '#0dbd7d',
      wickDownColor: '#f23d55',
    });

    // ── EMA overlays ──
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

    // ── Volume histogram (separate pane) ──
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat:        { type: 'volume' },
      priceScaleId:       'volume',
      lastValueVisible:   false,
      priceLineVisible:   false,
    });
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    chartRef.current = chart;

    // ── EMA lookup maps for legend ──
    let ema50Map  = new Map<string, number>();
    let ema200Map = new Map<string, number>();
    let barsMap   = new Map<string, OHLCBar>();

    // ── Crosshair → legend ──
    chart.subscribeCrosshairMove(param => {
      if (!param.time) { setLegend(null); return; }
      const t = param.time as string;
      const bar = barsMap.get(t);
      if (!bar) { setLegend(null); return; }
      setLegend({
        time: t, open: bar.open, high: bar.high, low: bar.low,
        close: bar.close, volume: bar.volume,
        ema50: ema50Map.get(t), ema200: ema200Map.get(t),
      });
    });

    // Fetch data
    fetch(`/api/v1/chart/${encodeURIComponent(symbol)}/daily`)
      .then(r => {
        if (!r.ok) throw new Error(`${r.status}`);
        return r.json();
      })
      .then((res: { candles: OHLCBar[] } | OHLCBar[]) => {
        const bars: OHLCBar[] = Array.isArray(res) ? res : res.candles;

        // Build lookup
        barsMap = new Map(bars.map(b => [b.time, b]));

        // Candles
        const candleData: CandlestickData<Time>[] = bars.map(b => ({
          time: b.time as Time, open: b.open, high: b.high, low: b.low, close: b.close,
        }));
        candleSeries.setData(candleData);

        // Volume
        const volData: HistogramData<Time>[] = bars.map(b => ({
          time:  b.time as Time,
          value: b.volume,
          color: b.close >= b.open ? 'rgba(13, 189, 125, 0.35)' : 'rgba(242, 61, 85, 0.35)',
        }));
        volumeSeries.setData(volData);

        // EMAs
        const ema50  = computeEMA(bars, 50);
        const ema200 = computeEMA(bars, 200);
        ema50Map  = new Map(ema50.map(p => [p.time, p.value]));
        ema200Map = new Map(ema200.map(p => [p.time, p.value]));
        if (ema50.length)  ema50Series.setData(ema50.map(p => ({ time: p.time as Time, value: p.value })));
        if (ema200.length) ema200Series.setData(ema200.map(p => ({ time: p.time as Time, value: p.value })));

        // Volume profile overlay
        const profile = buildVolumeProfile(bars);
        profileRef.current = profile;
        drawVolumeProfile(profile, candleSeries);

        // Redraw VP on visible range change (scroll / zoom)
        chart.timeScale().subscribeVisibleLogicalRangeChange(() => {
          drawVolumeProfile(profile, candleSeries);
        });

        chart.timeScale().fitContent();
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });

    const ro = new ResizeObserver(entries => {
      const { width, height: h } = entries[0].contentRect;
      chart.applyOptions({ width, height: h });
      drawVolumeProfile(profileRef.current, candleSeries);
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [symbol, height, drawVolumeProfile]);

  const fmtVol = (v: number) => {
    if (v >= 1e7) return `${(v / 1e7).toFixed(1)}Cr`;
    if (v >= 1e5) return `${(v / 1e5).toFixed(1)}L`;
    if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
    return String(v);
  };

  return (
    <div className="relative h-full">
      {/* Legend overlay */}
      <div className="absolute top-1 left-2 z-20 flex items-center gap-3 text-[9px] pointer-events-none">
        {legend ? (
          <>
            <span className="text-ghost">{legend.time}</span>
            <span className="text-ghost">O</span>
            <span className={legend.close >= legend.open ? 'text-bull' : 'text-bear'}>{legend.open.toFixed(2)}</span>
            <span className="text-ghost">H</span>
            <span className={legend.close >= legend.open ? 'text-bull' : 'text-bear'}>{legend.high.toFixed(2)}</span>
            <span className="text-ghost">L</span>
            <span className={legend.close >= legend.open ? 'text-bull' : 'text-bear'}>{legend.low.toFixed(2)}</span>
            <span className="text-ghost">C</span>
            <span className={legend.close >= legend.open ? 'text-bull' : 'text-bear'}>{legend.close.toFixed(2)}</span>
            <span className="text-ghost">Vol</span>
            <span className="text-dim">{fmtVol(legend.volume)}</span>
            {legend.ema50 != null && (
              <><span style={{ color: '#e8933a' }}>EMA50</span><span className="text-dim">{legend.ema50.toFixed(2)}</span></>
            )}
            {legend.ema200 != null && (
              <><span style={{ color: '#9b72f7' }}>EMA200</span><span className="text-dim">{legend.ema200.toFixed(2)}</span></>
            )}
          </>
        ) : (
          <div className="flex items-center gap-3">
            <span style={{ color: '#e8933a' }}>━ EMA50</span>
            <span style={{ color: '#9b72f7' }}>━ EMA200</span>
            <span style={{ color: 'rgba(13, 189, 125, 0.5)' }}>▮ Volume</span>
            <span style={{ color: 'rgba(147, 130, 220, 0.4)' }}>▮ VP</span>
          </div>
        )}
      </div>

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
      {/* Volume profile canvas overlay */}
      <canvas
        ref={vpCanvasRef}
        className="absolute inset-0 pointer-events-none z-[5]"
        style={{ width: '100%', height: '100%' }}
      />
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
    </div>
  );
});

DailyChart.displayName = 'DailyChart';
