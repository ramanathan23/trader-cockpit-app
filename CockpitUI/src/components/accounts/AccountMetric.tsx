import { money, tone } from './accountFmt';

export function AccountMetric({ label, value, signed }: { label: string; value: string | number | null | undefined; signed?: boolean }) {
  const numeric = typeof value === 'number';
  return (
    <div className="rounded-lg border border-border bg-panel px-3 py-3">
      <div className="text-[10px] font-black uppercase tracking-widest text-ghost">{label}</div>
      <div className={`num mt-2 text-[22px] font-black ${signed && numeric ? tone(value) : 'text-fg'}`}>
        {numeric ? money(value) : value ?? '-'}
      </div>
    </div>
  );
}
