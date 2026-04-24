'use client';

import { memo } from 'react';
import type { Timeframe } from '@/lib/chartUtils';
import { useDailyChart } from './useDailyChart';
import { ChartLegend } from './ChartLegend';
import { IndToggle } from './IndToggle';

interface DailyChartProps {
  symbol: string;
  height?: number | string;
}

const TF_GROUPS: Timeframe[][] = [
  ['1m', '3m', '5m', '15m', '1h'],
  ['1d', '1w', '1mo'],
];

export const DailyChart = memo(({ symbol, height = 300 }: DailyChartProps) => {
  const {
    tf, setTf, vis, toggle,
    loading, error, legend, setLegend,
    containerRef, vpCanvasRef,
    isIntraday, emaPeriods,
  } = useDailyChart(symbol, height);

  return (
    <div className="relative flex h-full flex-col">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border bg-panel/60 px-3 py-1.5">
        <div className="flex items-center gap-2">
          {TF_GROUPS.map((group, gi) => (
            <div key={gi} className="seg-group">
              {group.map(t => (
                <button key={t} type="button" onClick={() => { setTf(t); setLegend(null); }}
                  className={`seg-btn ${tf === t ? 'active' : ''}`}>
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

      <div className="relative flex-1 overflow-hidden">
        <ChartLegend legend={legend} vis={vis} isIntraday={isIntraday}
          fastLabel={emaPeriods.fastLabel} slowLabel={emaPeriods.slowLabel} />
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center text-[10px] text-ghost">
            Loading {tf}…
          </div>
        )}
        {error && (
          <div className="absolute inset-0 z-10 flex items-center justify-center text-[10px] text-bear">
            {error}
          </div>
        )}
        <canvas ref={vpCanvasRef} className="pointer-events-none absolute inset-0 z-[5]"
          style={{ width: '100%', height: '100%' }} />
        <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      </div>
    </div>
  );
});
DailyChart.displayName = 'DailyChart';
