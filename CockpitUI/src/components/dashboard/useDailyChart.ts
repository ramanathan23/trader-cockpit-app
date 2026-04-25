import { useCallback, useEffect, useRef, useState } from 'react';
import {
  createChart, CandlestickSeries, HistogramSeries, LineSeries,
  type IChartApi, type ISeriesApi,
  type CandlestickData, type HistogramData, type LineData, type Time,
} from 'lightweight-charts';
import {
  type Timeframe, type ChartBar,
  INTRADAY_TFS, buildChartUrl, tfEMAPeriods,
  computeEMA, resampleWeekly, resampleMonthly, buildVolumeProfile,
} from '@/lib/chartUtils';
import type { LegendData, IndicatorVis } from './ChartLegend';

export function useDailyChart(symbol: string, height: number | string) {
  const [tf,      setTf]      = useState<Timeframe>('1d');
  const [vis,     setVis]     = useState<IndicatorVis>({ ema50: true, ema200: true, vol: true, vp: true });
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);
  const [legend,  setLegend]  = useState<LegendData | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const vpCanvasRef  = useRef<HTMLCanvasElement>(null);
  const chartRef     = useRef<IChartApi | null>(null);
  const seriesRef    = useRef<{
    candle: ISeriesApi<'Candlestick'> | null;
    fast:   ISeriesApi<'Line'>        | null;
    slow:   ISeriesApi<'Line'>        | null;
    vol:    ISeriesApi<'Histogram'>   | null;
  }>({ candle: null, fast: null, slow: null, vol: null });
  const dataRef = useRef<{
    bars: ChartBar[];
    fast: LineData<Time>[];
    slow: LineData<Time>[];
    vol:  HistogramData<Time>[];
  }>({ bars: [], fast: [], slow: [], vol: [] });
  const visRef = useRef(vis);
  visRef.current = vis;

  const drawVP = useCallback((visibleBars: ChartBar[]) => {
    const canvas = vpCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr  = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width  = rect.width  * dpr;
    canvas.height = rect.height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);
    const series = seriesRef.current.candle;
    const chart  = chartRef.current;
    if (!series || !chart || !visRef.current.vp || visibleBars.length === 0) return;
    const profile    = buildVolumeProfile(visibleBars, 32);
    const pricePaneH = chart.panes()[0]?.getHeight() ?? rect.height;
    const maxBarW    = rect.width * 0.13;
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, rect.width, pricePaneH);
    ctx.clip();
    const barH = Math.max(1.5, pricePaneH / profile.length - 0.5);
    for (const row of profile) {
      const y = series.priceToCoordinate(row.price);
      if (y == null || y < 0 || y > pricePaneH) continue;
      ctx.fillStyle = row.pct > 0.65 ? 'rgba(147,130,220,0.42)' : 'rgba(147,130,220,0.17)';
      ctx.fillRect(rect.width - row.pct * maxBarW, y - barH / 2, row.pct * maxBarW, barH);
    }
    ctx.restore();
  }, []);

  const refreshVP = useCallback(() => {
    const chart = chartRef.current;
    const bars  = dataRef.current.bars;
    if (!chart || bars.length === 0) { drawVP([]); return; }
    const range = chart.timeScale().getVisibleLogicalRange();
    if (range) {
      const from = Math.max(0, Math.floor(range.from));
      const to   = Math.min(bars.length - 1, Math.ceil(range.to));
      drawVP(bars.slice(from, to + 1));
    } else {
      drawVP(bars);
    }
  }, [drawVP]);

  useEffect(() => {
    if (!containerRef.current) return;
    const isIntraday = INTRADAY_TFS.includes(tf);
    const emaPeriods = tfEMAPeriods(tf);
    const initH = containerRef.current.offsetHeight || (typeof height === 'number' ? height : 400);

    const chart = createChart(containerRef.current, {
      height: initH,
      layout:          { background: { color: 'transparent' }, textColor: 'rgb(116,142,170)', fontSize: 10 },
      grid:            { vertLines: { color: 'rgba(60,80,110,0.35)' }, horzLines: { color: 'rgba(60,80,110,0.35)' } },
      crosshair:       { vertLine: { color: 'rgba(45,126,232,0.3)', width: 1, style: 2 }, horzLine: { color: 'rgba(45,126,232,0.3)', width: 1, style: 2 } },
      timeScale:       { borderColor: 'rgba(40,55,80,0.8)', timeVisible: isIntraday, secondsVisible: false },
      rightPriceScale: { borderColor: 'rgba(40,55,80,0.8)' },
    });
    chartRef.current = chart;

    const candle     = chart.addSeries(CandlestickSeries, { upColor: '#0dbd7d', downColor: '#f23d55', borderUpColor: '#0dbd7d', borderDownColor: '#f23d55', wickUpColor: '#0dbd7d', wickDownColor: '#f23d55' });
    const fastSeries = chart.addSeries(LineSeries,        { color: '#e8933a', lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    const slowSeries = chart.addSeries(LineSeries,        { color: '#9b72f7', lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
    const volSeries  = chart.addSeries(HistogramSeries,   { priceFormat: { type: 'volume' }, priceScaleId: 'volume', lastValueVisible: false, priceLineVisible: false });
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    seriesRef.current = { candle, fast: fastSeries, slow: slowSeries, vol: volSeries };

    const barsMap = new Map<string | number, ChartBar>();
    const fastMap = new Map<string | number, number>();
    const slowMap = new Map<string | number, number>();

    chart.subscribeCrosshairMove(param => {
      if (!param.time) { setLegend(null); return; }
      const t = param.time as string | number;
      const bar = barsMap.get(t);
      if (!bar) { setLegend(null); return; }
      setLegend({ time: t, open: bar.open, high: bar.high, low: bar.low, close: bar.close, volume: bar.volume, fast: fastMap.get(t), slow: slowMap.get(t) });
    });
    chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (!range) return;
      const bars = dataRef.current.bars;
      drawVP(bars.slice(Math.max(0, Math.floor(range.from)), Math.min(bars.length - 1, Math.ceil(range.to)) + 1));
    });

    let aborted = false;
    setLoading(true); setError(null); setLegend(null);

    fetch(buildChartUrl(symbol, tf))
      .then(r => {
        if (!r.ok) throw new Error(r.status === 404 ? 'No data for this symbol / timeframe' : `HTTP ${r.status}`);
        return r.json();
      })
      .then((res: { candles: ChartBar[] }) => {
        if (aborted) return;
        let bars: ChartBar[] = res.candles;
        if (tf === '1w')  bars = resampleWeekly(bars);
        if (tf === '1mo') bars = resampleMonthly(bars);
        dataRef.current.bars = bars;
        bars.forEach(b => barsMap.set(b.time, b));
        candle.setData(bars.map(b => ({ time: b.time as Time, open: b.open, high: b.high, low: b.low, close: b.close })) as CandlestickData<Time>[]);
        const fastData = computeEMA(bars, emaPeriods.fast).map(p => ({ time: p.time as Time, value: p.value }));
        const slowData = computeEMA(bars, emaPeriods.slow).map(p => ({ time: p.time as Time, value: p.value }));
        dataRef.current.fast = fastData;
        dataRef.current.slow = slowData;
        fastData.forEach(p => fastMap.set(p.time as string | number, p.value));
        slowData.forEach(p => slowMap.set(p.time as string | number, p.value));
        if (visRef.current.ema50)  fastSeries.setData(fastData);
        if (visRef.current.ema200) slowSeries.setData(slowData);
        const volData: HistogramData<Time>[] = bars.map(b => ({
          time: b.time as Time, value: b.volume,
          color: b.close >= b.open ? 'rgba(13,189,125,0.35)' : 'rgba(242,61,85,0.35)',
        }));
        dataRef.current.vol = volData;
        if (visRef.current.vol) volSeries.setData(volData);
        if (isIntraday || tf === '1mo') {
          chart.timeScale().fitContent();
        } else {
          const lookback = tf === '1w' ? 52 : 90;
          const to   = bars.length - 0.5;
          const from = Math.max(-0.5, to - lookback);
          chart.timeScale().setVisibleLogicalRange({ from, to });
        }
        setLoading(false);
        requestAnimationFrame(() => drawVP(bars));
      })
      .catch(err => { if (!aborted) { setError(err.message); setLoading(false); } });

    const ro = new ResizeObserver(entries => {
      const { width, height: h } = entries[0].contentRect;
      chart.applyOptions({ width, height: h });
      refreshVP();
    });
    ro.observe(containerRef.current!);

    return () => {
      aborted = true;
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = { candle: null, fast: null, slow: null, vol: null };
    };
  }, [symbol, tf, height, drawVP, refreshVP]);

  useEffect(() => {
    const { fast, slow, vol } = seriesRef.current;
    if (!fast) return;
    const data = dataRef.current;
    fast.setData(vis.ema50  ? data.fast : []);
    slow?.setData(vis.ema200 ? data.slow : []);
    vol?.setData(vis.vol    ? data.vol  : []);
    refreshVP();
  }, [vis, refreshVP]);

  const toggle = (key: keyof IndicatorVis) => setVis(prev => ({ ...prev, [key]: !prev[key] }));

  return {
    tf, setTf, vis, toggle,
    loading, error, legend, setLegend,
    containerRef, vpCanvasRef,
    isIntraday: INTRADAY_TFS.includes(tf),
    emaPeriods: tfEMAPeriods(tf),
  };
}
