import type { Dashboard } from './accountTypes';
import { money } from './accountFmt';

export function ActivityBars({ daily }: { daily: Dashboard['daily'] }) {
  const totalExecutions = daily.reduce((sum, row) => sum + row.executions, 0);
  const max = Math.max(1, ...daily.map(row => Math.max(Math.abs(row.cashflow), row.executions)));
  const rows = daily.length ? daily : [{ date: 'No synced executions', cashflow: 0, executions: 0 }];
  return (
    <div className="h-44 rounded-lg border border-border bg-panel p-3">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[12px] font-black text-fg">Daily Activity Since Apr 2026</span>
        <span className="text-right">
          <span className="num block text-[13px] font-black text-fg">{money(totalExecutions)}</span>
          <span className="block text-[10px] text-ghost">execution count</span>
        </span>
      </div>
      <div className="flex h-28 items-end gap-1">
        {rows.slice(-28).map(row => {
          const h = Math.max(3, Math.max(Math.abs(row.cashflow), row.executions) / max * 100);
          return (
            <div key={row.date} className="group relative flex flex-1 items-end">
              <div className="w-full rounded-t bg-accent/70" style={{ height: `${h}%` }} />
              <div className="pointer-events-none absolute bottom-full left-1/2 z-10 hidden -translate-x-1/2 rounded border border-border bg-base px-2 py-1 text-[10px] text-fg group-hover:block">
                {row.date}: {row.executions} exec / {money(row.cashflow)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
