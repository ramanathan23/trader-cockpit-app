import type { ReactNode } from 'react';

export function OverviewHeader({
  loading, count, marketOpen, signalCount, highConviction, fnoCount, bullish, bearish,
}: {
  loading: boolean;
  count: number;
  marketOpen: boolean;
  signalCount: number;
  highConviction: number;
  fnoCount: number;
  bullish: number;
  bearish: number;
}) {
  return (
    <div className="border-b border-border bg-panel/88 px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="mr-auto min-w-[220px]">
          <div className="text-[15px] font-black text-fg">Market Attention</div>
          <div className="mt-0.5 text-[11px] text-ghost">
            {loading ? 'Loading universe...' : `${count} scored symbols`} - {marketOpen ? 'live prices active' : 'using latest synced data'}
          </div>
        </div>
        <Metric label="Signals" value={signalCount} tone="text-accent" />
        <Metric label="High Score" value={highConviction} tone="text-bull" />
        <Metric label="F&O" value={fnoCount} tone="text-violet" />
        <Metric label="Bull / Bear" value={`${bullish}/${bearish}`} tone={bullish >= bearish ? 'text-bull' : 'text-bear'} />
      </div>
    </div>
  );
}

export function Panel({
  title, caption, className, actions, children,
}: { title: string; caption: string; className?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className={`min-w-0 overflow-hidden rounded-lg border border-border bg-panel ${className ?? ''}`}>
      <div className="flex items-center justify-between gap-3 border-b border-border px-3 py-2">
        <div className="min-w-0">
          <div className="truncate text-[12px] font-black text-fg">{title}</div>
          <div className="truncate text-[10px] text-ghost">{caption}</div>
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

function Metric({ label, value, tone }: { label: string; value: number | string; tone: string }) {
  return (
    <div className="min-w-[86px] rounded border border-border bg-base/60 px-3 py-2">
      <div className="label-xs">{label}</div>
      <div className={`num mt-1 text-[18px] font-black leading-none ${tone}`}>{value}</div>
    </div>
  );
}
