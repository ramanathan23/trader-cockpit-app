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
  type TPOLevel,
  INTRADAY_TFS,
  PERIOD_COLORS,
  buildChartUrl,
  fmtBarTime,
  fmtVol,
  computeEMA,
  resampleWeekly,
  resampleMonthly,
  buildVolumeProfile,
  buildTPO,
  autoTickSize,
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
  ema50?: number;
  ema200?: number;
}

interface IndicatorVis {
  ema50: boolean;
  ema200: boolean;
  vol: boolean;
  vp: boolean;
  tpo: boolean;
}

// ── Timeframe groups for the toolbar ─────────────────────────────────────────

const TF_GROUPS: Timeframe[][] = [
  ['1m', '3m', '5m', '15m', '1h'],
  ['1d', '1w', '1mo'],
];

// ── Component ────────────────────────────────────────────────────────────────

export const DailyChart = memo(({ symbol, height = 300 }: DailyChartProps) => {
  const [tf, setTf]       = useState<Timeframe>('1d');
  const [vis, setVis]     = useState<IndicatorVis>({ ema50: true, ema200: true, vol: true, vp: true, tpo: false });
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);
  const [legend,  setLegend]  = useState<LegendData | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const vpCanvasRef  = useRef<HTMLCanvasElement>(null);
  const tpoCanvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef     = useRef<IChartApi | null>(null);

  const seriesRef = useRef<{
    candle: ISeriesApi<'Candlestick'> | null;
    ema50:  ISeriesApi<'Line'>        | null;
    ema200: ISeriesApi<'Line'>        | null;
    vol:    ISeriesApi<'Histogram'>   | null;
  }>({ candle: null, ema50: null, ema200: null, vol: null });

  const dataRef = useRef<{
    bars:    ChartBar[];
    ema50:   LineData<Time>[];
    ema200:  LineData<Time>[];
    vol:     HistogramData<Time>[];
    tpo:     TPOLevel[];
    tickSz:  number;
  }>({ bars: [], ema50: [], ema200: [], vol: [], tpo: [], tickSz: 1 });

  // always-current ref so callbacks don't capture stale vis
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
      const barW = row.pct * maxBarW;
      ctx.fillStyle = row.pct > 0.65
        ? 'rgba(147,130,220,0.42)'
        : 'rgba(147,130,220,0.17)';
      ctx.fillRect(rect.width - barW, y - barH / 2, barW, barH);
    }
    ctx.restore();
  }, []);

  // ── TPO draw ─────────────────────────────────────────────────────────────

  const drawTPO = useCallback(() => {
    const canvas = tpoCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr  = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width  = rect.width  * dpr;
    canvas.height = rect.height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);

    const levels = dataRef.current.tpo;
    const series = seriesRef.current.candle;
    const chart  = chartRef.current;
    if (!series || !chart || !visRef.current.tpo || levels.length === 0) return;

    const pricePaneH = chart.panes()[0]?.getHeight() ?? rect.height;
    const maxPeriod  = Math.max(...levels.flatMap(l => l.periods), 0);
    const colW       = Math.max(5, Math.min(9, rect.width * 0.018));

    // estimate row height from tick size
    const tickSz = dataRef.current.tickSz;
    const sampleY1 = series.priceToCoordinate(levels[levels.length - 1].price);
    const sampleY2 = series.priceToCoordinate(levels[levels.length - 1].price + tickSz);
    const rowH = sampleY1 != null && sampleY2 != null
      ? Math.max(2, Math.abs(sampleY2 - sampleY1))
      : colW;

    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, (maxPeriod + 1) * colW + 2, pricePaneH);
    ctx.clip();

    for (const level of levels) {
      const y = series.priceToCoordinate(level.price);
      if (y == null || y < 0 || y > pricePaneH) continue;
      for (const pIdx of level.periods) {
        const x = pIdx * colW;
        ctx.fillStyle = PERIOD_COLORS[pIdx % PERIOD_COLORS.length] + '77';
        ctx.fillRect(x, y - rowH / 2, colW - 0.5, rowH);
      }
    }
    ctx.restore();
  }, []);

  // ── Helper: refresh both overlays with current visible range ─────────────

  const refreshOverlays = useCallback(() => {
    const chart = chartRef.current;
    const bars  = dataRef.current.bars;
    if (!chart || bars.length === 0) return;
    const range = chart.timeScale().getVisibleLogicalRange();
    if (range) {
      const from = Math.max(0, Math.floor(range.from));
      const to   = Math.min(bars.length - 1, Math.ceil(range.to));
      drawVP(bars.slice(from, to + 1));
    } else {
      drawVP(bars);
    }
    drawTPO();
  }, [drawVP, drawTPO]);

  // ── Chart creation + data load — reruns on symbol or TF change ───────────

  useEffect(() => {
    if (!containerRef.current) return;

    const isIntraday = INTRADAY_TFS.includes(tf);
    const initH = containerRef.current.offsetHeight || (typeof height === 'number' ? height : 400);

    const chart = createChart(containerRef.current, {
      height: initH,
      layout: {
        background: { color: 'transparent' },
        textColor: 'rgb(116,142,170)',
        fontSize: 10,
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
        borderColor: 'rgba(40,55,80,0.8)',
        timeVisible: isIntraday,
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
    const ema50s = chart.addSeries(LineSeries, {
      color: '#e8933a', lineWidth: 1,
      priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
    });
    const ema200s = chart.addSeries(LineSeries, {
      color: '#9b72f7', lineWidth: 1,
      priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
    });
    const volSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' }, priceScaleId: 'volume',
      lastValueVisible: false, priceLineVisible: false,
    });
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

    seriesRef.current = { candle, ema50: ema50s, ema200: ema200s, vol: volSeries };

    // crosshair → legend
    const barsMap = new Map<string | number, ChartBar>();
    const ema50Map  = new Map<string | number, number>();
    const ema200Map = new Map<string | number, number>();
    chart.subscribeCrosshairMove(param => {
      if (!param.time) { setLegend(null); return; }
      const t = param.time as string | number;
      const bar = barsMap.get(t);
      if (!bar) { setLegend(null); return; }
      setLegend({
        time: t, open: bar.open, high: bar.high, low: bar.low,
        close: bar.close, volume: bar.volume,
        ema50: ema50Map.get(t), ema200: ema200Map.get(t),
      });
    });

    // VP refresh on scroll/zoom
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

    fetch(buildChartUrl(symbol, tf))
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then((res: { candles: ChartBar[] }) => {
        if (aborted) return;

        let bars: ChartBar[] = res.candles;
        if (tf === '1w')  bars = resampleWeekly(bars);
        if (tf === '1mo') bars = resampleMonthly(bars);

        dataRef.current.bars = bars;
        bars.forEach(b => barsMap.set(b.time, b));

        // candles
        candle.setData(bars.map(b => ({
          time: b.time as Time, open: b.open, high: b.high, low: b.low, close: b.close,
        })) as CandlestickData<Time>[]);

        // EMAs
        const e50  = computeEMA(bars, 50).map(p => ({ time: p.time as Time, value: p.value }));
        const e200 = computeEMA(bars, 200).map(p => ({ time: p.time as Time, value: p.value }));
        dataRef.current.ema50  = e50;
        dataRef.current.ema200 = e200;
        e50.forEach(p  => ema50Map.set(p.time as string | number, p.value));
        e200.forEach(p => ema200Map.set(p.time as string | number, p.value));
        if (visRef.current.ema50)  ema50s.setData(e50);
        if (visRef.current.ema200) ema200s.setData(e200);

        // volume
        const volData: HistogramData<Time>[] = bars.map(b => ({
          time: b.time as Time,
          value: b.volume,
          color: b.close >= b.open ? 'rgba(13,189,125,0.35)' : 'rgba(242,61,85,0.35)',
        }));
        dataRef.current.vol = volData;
        if (visRef.current.vol) volSeries.setData(volData);

        // TPO (intraday only)
        if (isIntraday && bars.length > 0) {
          const mid    = (bars[bars.length - 1].high + bars[bars.length - 1].low) / 2;
          const tickSz = autoTickSize(mid);
          dataRef.current.tickSz = tickSz;
          dataRef.current.tpo    = buildTPO(bars, tickSz, 30);
        } else {
          dataRef.current.tpo   = [];
          dataRef.current.tickSz = 1;
        }

        chart.timeScale().fitContent();
        setLoading(false);

        // initial overlay draw (all bars)
        requestAnimationFrame(() => {
          drawVP(bars);
          drawTPO();
        });
      })
      .catch(err => {
        if (!aborted) { setError(err.message); setLoading(false); }
      });

    const ro = new ResizeObserver(entries => {
      const { width, height: h } = entries[0].contentRect;
      chart.applyOptions({ width, height: h });
      refreshOverlays();
    });
    ro.observe(containerRef.current);

    return () => {
      aborted = true;
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = { candle: null, ema50: null, ema200: null, vol: null };
    };
  }, [symbol, tf, height, drawVP, drawTPO, refreshOverlays]);

  // ── Indicator visibility changes ─────────────────────────────────────────

  useEffect(() => {
    const { ema50: e50s, ema200: e200s, vol: vols } = seriesRef.current;
    const data = dataRef.current;
    if (!e50s) return; // chart not yet created

    e50s.setData(vis.ema50  ? data.ema50  : []);
    e200s?.setData(vis.ema200 ? data.ema200 : []);
    vols?.setData(vis.vol   ? data.vol   : []);

    refreshOverlays();
  }, [vis, refreshOverlays]);

  // ── Indicator toggle helper ───────────────────────────────────────────────

  const toggle = (key: keyof IndicatorVis) =>
    setVis(prev => ({ ...prev, [key]: !prev[key] }));

  const isIntraday = INTRADAY_TFS.includes(tf);

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="relative flex h-full flex-col">

      {/* ── Toolbars ── */}
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border bg-panel/60 px-3 py-1.5">
        {/* timeframe selector */}
        <div className="flex items-center gap-2">
          {TF_GROUPS.map((group, gi) => (
            <div key={gi} className="seg-group">
              {group.map(t => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTf(t)}
                  className={`seg-btn ${tf === t ? 'active' : ''}`}
                >
                  {t}
                </button>
              ))}
            </div>
          ))}
        </div>

        {/* indicator toggles */}
        <div className="flex items-center gap-1">
          <IndToggle label="EMA50"  color="#e8933a" on={vis.ema50}  onClick={() => toggle('ema50')} />
          <IndToggle label="EMA200" color="#9b72f7" on={vis.ema200} onClick={() => toggle('ema200')} />
          <IndToggle label="Vol"    color="rgba(13,189,125,0.7)" on={vis.vol}   onClick={() => toggle('vol')} />
          <IndToggle label="VP"     color="rgba(147,130,220,0.8)" on={vis.vp}  onClick={() => toggle('vp')} />
          <IndToggle
            label="TPO"
            color={PERIOD_COLORS[2]}
            on={vis.tpo}
            onClick={() => toggle('tpo')}
            disabled={!isIntraday}
            title={isIntraday ? undefined : 'TPO requires intraday timeframe'}
          />
        </div>
      </div>

      {/* ── Chart area ── */}
      <div className="relative flex-1 overflow-hidden">

        {/* legend */}
        <div className="absolute top-1 left-2 z-20 flex flex-wrap items-center gap-2 text-[9px] pointer-events-none">
          {legend ? (
            <>
              <span className="text-ghost">{fmtBarTime(legend.time, isIntraday)}</span>
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
              {legend.ema50  != null && <><span style={{ color: '#e8933a' }}>EMA50</span><span className="text-dim">{legend.ema50.toFixed(2)}</span></>}
              {legend.ema200 != null && <><span style={{ color: '#9b72f7' }}>EMA200</span><span className="text-dim">{legend.ema200.toFixed(2)}</span></>}
            </>
          ) : (
            <div className="flex items-center gap-2">
              {vis.ema50  && <span style={{ color: '#e8933a' }}>━ EMA50</span>}
              {vis.ema200 && <span style={{ color: '#9b72f7' }}>━ EMA200</span>}
              {vis.vol    && <span style={{ color: 'rgba(13,189,125,0.6)' }}>▮ Vol</span>}
              {vis.vp     && <span style={{ color: 'rgba(147,130,220,0.6)' }}>▮ VP</span>}
              {vis.tpo && isIntraday && <span style={{ color: PERIOD_COLORS[0] }}>▮ TPO</span>}
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
            Chart error: {error}
          </div>
        )}

        {/* TPO canvas — left side, behind VP */}
        <canvas
          ref={tpoCanvasRef}
          className="absolute inset-0 pointer-events-none z-[4]"
          style={{ width: '100%', height: '100%' }}
        />
        {/* VP canvas — right side, in front of TPO */}
        <canvas
          ref={vpCanvasRef}
          className="absolute inset-0 pointer-events-none z-[5]"
          style={{ width: '100%', height: '100%' }}
        />

        <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      </div>
    </div>
  );
});

DailyChart.displayName = 'DailyChart';

// ── Indicator toggle button ───────────────────────────────────────────────────

function IndToggle({
  label, color, on, onClick, disabled, title,
}: {
  label: string;
  color: string;
  on: boolean;
  onClick: () => void;
  disabled?: boolean;
  title?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`seg-btn flex items-center gap-1 text-[9px] ${on ? 'active' : ''} ${disabled ? 'opacity-30 cursor-not-allowed' : ''}`}
    >
      <span
        style={{
          display: 'inline-block', width: 8, height: 8,
          borderRadius: 1,
          background: on ? color : 'transparent',
          border: `1px solid ${color}`,
          flexShrink: 0,
        }}
      />
      {label}
    </button>
  );
}
