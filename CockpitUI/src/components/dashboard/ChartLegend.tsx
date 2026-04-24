'use client';

import { memo } from 'react';
import { fmtBarTime, fmtVol } from '@/lib/chartUtils';

export interface LegendData {
  time: string | number;
  open: number; high: number; low: number; close: number; volume: number;
  fast?: number; slow?: number;
}

export interface IndicatorVis {
  ema50: boolean; ema200: boolean; vol: boolean; vp: boolean;
}

interface ChartLegendProps {
  legend: LegendData | null;
  vis: IndicatorVis;
  isIntraday: boolean;
  fastLabel: string;
  slowLabel: string;
}

export const ChartLegend = memo(({ legend, vis, isIntraday, fastLabel, slowLabel }: ChartLegendProps) => {
  const cls = (l: LegendData) => l.close >= l.open ? 'text-bull' : 'text-bear';

  return (
    <div className="pointer-events-none absolute left-2 top-1 z-20 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[9px]">
      {legend ? (
        <>
          <span className="text-ghost">{fmtBarTime(legend.time, isIntraday)}</span>
          <span className="text-ghost">O</span><span className={cls(legend)}>{legend.open.toFixed(2)}</span>
          <span className="text-ghost">H</span><span className={cls(legend)}>{legend.high.toFixed(2)}</span>
          <span className="text-ghost">L</span><span className={cls(legend)}>{legend.low.toFixed(2)}</span>
          <span className="text-ghost">C</span><span className={cls(legend)}>{legend.close.toFixed(2)}</span>
          <span className="text-ghost">Vol</span><span className="text-dim">{fmtVol(legend.volume)}</span>
          {legend.fast != null && <><span style={{ color: '#e8933a' }}>{fastLabel}</span><span className="text-dim">{legend.fast.toFixed(2)}</span></>}
          {legend.slow != null && <><span style={{ color: '#9b72f7' }}>{slowLabel}</span><span className="text-dim">{legend.slow.toFixed(2)}</span></>}
        </>
      ) : (
        <div className="flex items-center gap-2">
          {vis.ema50  && <span style={{ color: '#e8933a' }}>━ {fastLabel}</span>}
          {vis.ema200 && <span style={{ color: '#9b72f7' }}>━ {slowLabel}</span>}
          {vis.vol    && <span style={{ color: 'rgba(13,189,125,0.6)' }}>▮ Vol</span>}
          {vis.vp     && <span style={{ color: 'rgba(147,130,220,0.6)' }}>▮ VP</span>}
        </div>
      )}
    </div>
  );
});
ChartLegend.displayName = 'ChartLegend';
