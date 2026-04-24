'use client';

import { memo } from 'react';
import { signalColor } from '@/domain/signal';

const SIGNAL_ROWS = [
  { key: 'RANGE_BREAKOUT',  label: 'RNG+',   desc: 'Rectangle consolidation broke upward on volume.' },
  { key: 'RANGE_BREAKDOWN', label: 'RNG-',   desc: 'Rectangle consolidation broke downward on volume.' },
  { key: 'CAM_H4_BREAKOUT', label: 'CAM H4+', desc: 'Closed above H4 on volume — narrow pivot range.' },
  { key: 'CAM_L4_BREAKDOWN',label: 'CAM L4-', desc: 'Closed below L4 on volume — narrow pivot range.' },
  { key: 'CAM_H4_REVERSAL', label: 'CAM H4↓', desc: 'Bearish pin rejection at H4 — wide pivot range.' },
  { key: 'CAM_H3_REVERSAL', label: 'CAM H3↓', desc: 'Bearish pin rejection at H3 — wide pivot range.' },
  { key: 'CAM_L3_REVERSAL', label: 'CAM L3↑', desc: 'Bullish pin bounce from L3 — wide pivot range.' },
  { key: 'CAM_L4_REVERSAL', label: 'CAM L4↑', desc: 'Bullish pin bounce from L4 — wide pivot range.' },
] as const;

const METRIC_ROWS = [
  { key: '52H', desc: 'Distance from the 52-week high.' },
  { key: '52L', desc: 'Distance from the 52-week low.' },
  { key: 'ATR', desc: '14-day average true range for stop sizing.' },
  { key: 'ADV', desc: '20-day average daily traded value in crores.' },
  { key: 'VOL', desc: 'Volume ratio versus normal activity.' },
  { key: 'MTF', desc: '15m and 1h directional alignment.' },
];

const PHASE_ROWS = [
  { key: 'Drive window', time: '09:15-09:45', color: 'rgb(var(--accent))', desc: 'Fast, opening momentum.' },
  { key: 'Execution', time: '09:45-11:30', color: 'rgb(var(--bull))', desc: 'Cleaner signal context.' },
  { key: 'Dead zone', time: '11:30-14:30', color: 'rgb(var(--ghost))', desc: 'Lower conviction chop.' },
  { key: 'Close momentum', time: '14:30-15:15', color: 'rgb(var(--amber))', desc: 'Late directional flow.' },
  { key: 'Session end', time: '15:15-15:30', color: 'rgb(var(--bear))', desc: 'Avoid fresh unplanned risk.' },
];

export const HelpLegend = memo(() => (
  <div className="shrink-0 border-b border-border bg-panel/90 px-5 py-4">
    <div className="grid gap-5 xl:grid-cols-[1.25fr_1fr_1fr]">
      <section>
        <SectionTitle>Signals</SectionTitle>
        <div className="help-signal-grid mt-3">
          {SIGNAL_ROWS.map(row => {
            const color = signalColor(row.key);
            return (
              <div key={row.key} className="flex gap-2">
                <span className="w-16 shrink-0 text-[10px] font-black" style={{ color }}>{row.label}</span>
                <span className="text-[11px] leading-snug text-dim">{row.desc}</span>
              </div>
            );
          })}
        </div>
      </section>

      <section>
        <SectionTitle>Metrics</SectionTitle>
        <div className="help-pair-grid mt-3">
          {METRIC_ROWS.map(row => <LegendRow key={row.key} label={row.key} desc={row.desc} />)}
          <LegendRow label="E" desc="Entry zone." color="rgb(var(--amber))" />
          <LegendRow label="SL" desc="Stop loss." color="rgb(var(--bear))" />
          <LegendRow label="T1" desc="First target." color="rgb(var(--bull))" />
        </div>
      </section>

      <section>
        <SectionTitle>Market Phases</SectionTitle>
        <div className="mt-3 flex flex-col gap-2">
          {PHASE_ROWS.map(row => (
            <div key={row.key} className="grid grid-cols-[104px_76px_1fr] gap-2 text-[11px]">
              <span className="font-black" style={{ color: row.color }}>{row.key}</span>
              <span className="num text-ghost">{row.time}</span>
              <span className="text-dim">{row.desc}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  </div>
));

HelpLegend.displayName = 'HelpLegend';

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-[10px] font-black uppercase text-ghost">{children}</h2>;
}

function LegendRow({ label, desc, color = 'rgb(var(--fg))' }: { label: string; desc: string; color?: string }) {
  return (
    <div className="flex gap-2">
      <span className="num w-9 shrink-0 text-[10px] font-black" style={{ color }}>{label}</span>
      <span className="text-[11px] leading-snug text-dim">{desc}</span>
    </div>
  );
}
