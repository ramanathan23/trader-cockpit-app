'use client';

export type ScoreColor = 'accent' | 'amber' | 'bull' | 'bear' | 'violet' | 'sky' | 'ghost';

/** Horizontal progress bar with numeric value — used in both card and table views. */
export function ScoreBar({ value, color, label }: { value: number; color: ScoreColor; label?: string }) {
  const pct     = Math.min(100, Math.max(0, value));
  const cssColor = `rgb(var(--${color}))`;
  return (
    <div className="flex items-center gap-2">
      {label && <span className="label-xs w-9 shrink-0">{label}</span>}
      <div className="flex flex-1 items-center justify-end gap-2">
        <span className="num text-[12px] font-black" style={{ color: cssColor }}>{value.toFixed(0)}</span>
        <div className="h-2 w-[72px] overflow-hidden rounded-full bg-border/60">
          <div className="h-full rounded-full" style={{ width: `${pct}%`, background: cssColor }} />
        </div>
      </div>
    </div>
  );
}
