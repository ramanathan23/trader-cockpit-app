'use client';

import { memo, useCallback, useEffect, useRef, useState } from 'react';
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type HistogramData,
  type LineData,
  type Time,
} from 'lightweight-charts';
import {
  type Timeframe,
  type ChartBar,
  type ProfileRow,
  INTRADAY_TFS,
  buildChartUrl,
  tfEMAPeriods,
  fmtBarTime,
  fmtVol,
  computeEMA,
  resampleWeekly,
  resampleMonthly,
  buildVolumeProfile,
} from '@/lib/chartUtils';

// ── Types ────────────────────────────────────────────────────────────────────

interface DailyChartProps {
  symbol: string;
  height?: number | string;
}

interface LegendData {
  time: string | number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  fast?: number;
  slow?: number;
}

interface IndicatorVis {
  ema50: boolean;
  ema200: boolean;
  vol: boolean;
  vp: boolean;
}

const TF_GROUPS: Timeframe[][] = [
  ['1m', '3m', '5m', '15m', '1h'],
  ['1d', '1w', '1mo'],
];

// ── Component ────────────────────────────────────────────────────────────────

export const DailyChart = memo(({ symbol, height = 300 }: DailyChartProps) => {
  const [tf, setTf]       = useState<Timeframe>('1d');
  const [vis, setVis]     = useState<IndicatorVis>({ ema50: true, ema200: true, vol: true, vp: true });
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);
  const [legend,  setLegend]  = useState<LegendData | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const vpCanvasRef  = useRef<HTMLCanvasElement>(null);
  const chartRef     = useRef<IChartApi | null>(null);

  const seriesRef = useRef<{
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

  // ── VP draw ──────────────────────────────────────────────────────────────

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

    const profile: ProfileRow[] = buildVolumeProfile(visibleBars, 32);
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
      ctx.fillStyle = row.pct > 0.65
        ? 'rgba(147,130,220,0.42)'
        : 'rgba(147,130,220,0.17)';
      ctx.fillRect(rect.width - row.pct * maxBarW, y - barH / 2, row.pct * maxBarW, barH);
    }
    ctx.restore();
  }, []);

  // ── Refresh VP with current visible range ─────────────────────────────────

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

  // ── Main effect: create chart + load data ─────────────────────────────────

  useEffect(() => {
    if (!containerRef.current) return;

    const isIntraday = INTRADAY_TFS.includes(tf);
    const emaPeriods = tfEMAPeriods(tf);
    const initH = containerRef.current.offsetHeight || (typeof height === 'number' ? height : 400);

    const chart = createChart(containerRef.current, {
      height: initH,
      layout: {
        background: { color: 'transparent' },
        textColor:  'rgb(116,142,170)',
        fontSize:   10,
      },
      grid: {
        vertLines: { color: 'rgba(60,80,110,0.35)' },
        horzLines: { color: 'rgba(60,80,110,0.35)' },
      },
      crosshair: {
        vertLine: { color: 'rgba(45,126,232,0.3)', width: 1, style: 2 },
        horzLine: { color: 'rgba(45,126,232,0.3)', width: 1, style: 2 },
      },
      timeScale: {
        borderColor:    'rgba(40,55,80,0.8)',
        timeVisible:    isIntraday,
        secondsVisible: false,
      },
      rightPriceScale: { borderColor: 'rgba(40,55,80,0.8)' },
    });
    chartRef.current = chart;

    const candle = chart.addSeries(CandlestickSeries, {
      upColor: '#0dbd7d', downColor: '#f23d55',
      borderUpColor: '#0dbd7d', borderDownColor: '#f23d55',
      wickUpColor: '#0dbd7d', wickDownColor: '#f23d55',
    });
    const fastSeries = chart.addSeries(LineSeries, {
      color: '#e8933a', lineWidth: 1,
      priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
    });
    const slowSeries = chart.addSeries(LineSeries, {
      color: '#9b72f7', lineWidth: 1,
      priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
    });
    const volSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' }, priceScaleId: 'volume',
      lastValueVisible: false, priceLineVisible: false,
    });
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
      setLegend({
        time: t, open: bar.open, high: bar.high, low: bar.low,
        close: bar.close, volume: bar.volume,
        fast: fastMap.get(t), slow: slowMap.get(t),
      });
    });

    chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (!range) return;
      const bars = dataRef.current.bars;
      const from = Math.max(0, Math.floor(range.from));
      const to   = Math.min(bars.length - 1, Math.ceil(range.to));
      drawVP(bars.slice(from, to + 1));
    });

    let aborted = false;
    setLoading(true);
    setError(null);
    setLegend(null);

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

        candle.setData(bars.map(b => ({
          time: b.time as Time, open: b.open, high: b.high, low: b.low, close: b.close,
        })) as CandlestickData<Time>[]);

        const fastData = computeEMA(bars, emaPeriods.fast).map(p => ({ time: p.time as Time, value: p.value }));
        const slowData = computeEMA(bars, emaPeriods.slow).map(p => ({ time: p.time as Time, value: p.value }));
        dataRef.current.fast = fastData;
        dataRef.current.slow = slowData;
        fastData.forEach(p => fastMap.set(p.time as string | number, p.value));
        slowData.forEach(p => slowMap.set(p.time as string | number, p.value));
        if (visRef.current.ema50)  fastSeries.setData(fastData);
        if (visRef.current.ema200) slowSeries.setData(slowData);

        const volData: HistogramData<Time>[] = bars.map(b => ({
          time:  b.time as Time,
          value: b.volume,
          color: b.close >= b.open ? 'rgba(13,189,125,0.35)' : 'rgba(242,61,85,0.35)',
        }));
        dataRef.current.vol = volData;
        if (visRef.current.vol) volSeries.setData(volData);

        chart.timeScale().fitContent();
        setLoading(false);

        requestAnimationFrame(() => drawVP(bars));
      })
      .catch(err => {
        if (!aborted) { setError(err.message); setLoading(false); }
      });

    const ro = new ResizeObserver(entries => {
      const { width, height: h } = entries[0].contentRect;
      chart.applyOptions({ width, height: h });
      refreshVP();
    });
    ro.observe(containerRef.current);

    return () => {
      aborted = true;
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = { candle: null, fast: null, slow: null, vol: null };
    };
  }, [symbol, tf, height, drawVP, refreshVP]);

  // ── Indicator visibility changes ─────────────────────────────────────────

  useEffect(() => {
    const { fast, slow, vol } = seriesRef.current;
    if (!fast) return;
    const data = dataRef.current;
    fast.setData(vis.ema50  ? data.fast : []);
    slow?.setData(vis.ema200 ? data.slow : []);
    vol?.setData(vis.vol    ? data.vol  : []);
    refreshVP();
  }, [vis, refreshVP]);

  // ── Helpers ───────────────────────────────────────────────────────────────

  const toggle = (key: keyof IndicatorVis) =>
    setVis(prev => ({ ...prev, [key]: !prev[key] }));

  const isIntraday = INTRADAY_TFS.includes(tf);
  const emaPeriods = tfEMAPeriods(tf);

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="relative flex h-full flex-col">

      {/* ── Toolbars ── */}
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border bg-panel/60 px-3 py-1.5">
        <div className="flex items-center gap-2">
          {TF_GROUPS.map((group, gi) => (
            <div key={gi} className="seg-group">
              {group.map(t => (
                <button
                  key={t}
                  type="button"
                  onClick={() => { setTf(t); setLegend(null); }}
                  className={`seg-btn ${tf === t ? 'active' : ''}`}
                >
                  {t}
                </button>
              ))}
            </div>
          ))}
        </div>

        <div className="flex items-center gap-1">
          <IndToggle label={emaPeriods.fastLabel} color="#e8933a"               on={vis.ema50}  onClick={() => toggle('ema50')} />
          <IndToggle label={emaPeriods.slowLabel} color="#9b72f7"               on={vis.ema200} onClick={() => toggle('ema200')} />
          <IndToggle label="Vol"                  color="rgba(13,189,125,0.8)"  on={vis.vol}    onClick={() => toggle('vol')} />
          <IndToggle label="VP"                   color="rgba(147,130,220,0.9)" on={vis.vp}     onClick={() => toggle('vp')} />
        </div>
      </div>

      {/* ── Chart area ── */}
      <div className="relative flex-1 overflow-hidden">

        {/* legend */}
        <div className="absolute top-1 left-2 z-20 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[9px] pointer-events-none">
          {legend ? (
            <>
              <span className="text-ghost">{fmtBarTime(legend.time, isIntraday)}</span>
              <span className="text-ghost">O</span><span className={legend.close >= legend.open ? 'text-bull' : 'text-bear'}>{legend.open.toFixed(2)}</span>
              <span className="text-ghost">H</span><span className={legend.close >= legend.open ? 'text-bull' : 'text-bear'}>{legend.high.toFixed(2)}</span>
              <span className="text-ghost">L</span><span className={legend.close >= legend.open ? 'text-bull' : 'text-bear'}>{legend.low.toFixed(2)}</span>
              <span className="text-ghost">C</span><span className={legend.close >= legend.open ? 'text-bull' : 'text-bear'}>{legend.close.toFixed(2)}</span>
              <span className="text-ghost">Vol</span><span className="text-dim">{fmtVol(legend.volume)}</span>
              {legend.fast != null && <><span style={{ color: '#e8933a' }}>{emaPeriods.fastLabel}</span><span className="text-dim">{legend.fast.toFixed(2)}</span></>}
              {legend.slow != null && <><span style={{ color: '#9b72f7' }}>{emaPeriods.slowLabel}</span><span className="text-dim">{legend.slow.toFixed(2)}</span></>}
            </>
          ) : (
            <div className="flex items-center gap-2">
              {vis.ema50  && <span style={{ color: '#e8933a' }}>━ {emaPeriods.fastLabel}</span>}
              {vis.ema200 && <span style={{ color: '#9b72f7' }}>━ {emaPeriods.slowLabel}</span>}
              {vis.vol    && <span style={{ color: 'rgba(13,189,125,0.6)' }}>▮ Vol</span>}
              {vis.vp     && <span style={{ color: 'rgba(147,130,220,0.6)' }}>▮ VP</span>}
            </div>
          )}
        </div>

        {loading && (
          <div className="absolute inset-0 flex items-center justify-center text-[10px] text-ghost z-10">
            Loading {tf}…
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center text-[10px] text-bear z-10">
            {error}
          </div>
        )}

        <canvas ref={vpCanvasRef} className="absolute inset-0 pointer-events-none z-[5]" style={{ width: '100%', height: '100%' }} />
        <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      </div>
    </div>
  );
});

DailyChart.displayName = 'DailyChart';

// ── Indicator toggle button ───────────────────────────────────────────────────

function IndToggle({ label, color, on, onClick }: {
  label: string; color: string; on: boolean; onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`seg-btn flex items-center gap-1 text-[9px] ${on ? 'active' : ''}`}
    >
      <span style={{
        display: 'inline-block', width: 8, height: 8, borderRadius: 1, flexShrink: 0,
        background: on ? color : 'transparent',
        border: `1px solid ${color}`,
      }} />
      {label}
    </button>
  );
}
