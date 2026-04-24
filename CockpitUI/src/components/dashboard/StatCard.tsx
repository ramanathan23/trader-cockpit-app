'use client';

/** Summary metric tile shown in the dashboard header stats row. */
export function StatCard({ label, value, tone, title }: {
  label: string;
  value: string | number;
  tone?: 'bull' | 'accent';
  title?: string;
}) {
  const color = tone === 'bull' ? 'rgb(var(--bull))' : tone === 'accent' ? 'rgb(var(--accent))' : 'rgb(var(--fg))';
  return (
    <div className="metric-card" title={title}>
      <div className="text-[10px] font-black uppercase text-ghost">{label}</div>
      <div className="num mt-1 truncate text-[19px] font-black" style={{ color }}>{value}</div>
    </div>
  );
}
