'use client';

import { memo } from 'react';
import { signalColor } from '@/domain/signal';
import { SIGNAL_ROWS, METRIC_ROWS, PHASE_ROWS, SESSION_ROWS } from './helpLegendData';

export const HelpLegend = memo(() => (
  <div className="shrink-0 border-b border-border bg-panel/90 px-5 py-4">
    <div className="grid gap-5 xl:grid-cols-[1.25fr_1fr_1fr_1fr]">
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
          <LegendRow label="E"  desc="Entry zone."   color="rgb(var(--amber))" />
          <LegendRow label="SL" desc="Stop loss."    color="rgb(var(--bear))" />
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

      <section>
        <SectionTitle>Session Types</SectionTitle>
        <div className="mt-3 flex flex-col gap-2">
          {SESSION_ROWS.map(row => (
            <div key={row.key} className="flex gap-2">
              <span className="w-20 shrink-0 text-[10px] font-black" style={{ color: row.color }}>
                {row.key.replace('_', ' ')}
              </span>
              <span className="text-[11px] leading-snug text-dim">{row.desc}</span>
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
