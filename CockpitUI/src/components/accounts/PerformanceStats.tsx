import type { DashboardAccount } from './accountTypes';
import { money, tone } from './accountFmt';

function Cell({ label, value, toneClass = 'text-fg' }: { label: string; value: string | number; toneClass?: string }) {
  return (
    <div className="rounded border border-border bg-base px-3 py-2">
      <div className="label-xs mb-1">{label}</div>
      <div className={`num text-[16px] font-black ${toneClass}`}>{value}</div>
    </div>
  );
}

export function PerformanceStats({ account }: { account: DashboardAccount }) {
  return (
    <div className="rounded-lg border border-border bg-panel p-4">
      <div className="mb-3 text-[13px] font-black text-fg">Trade Behavior</div>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        <Cell label="Avg Trades / Day" value={account.avg_trades_per_day} />
        <Cell label="Winning Days" value={`${account.winning_days} @ ${account.avg_trades_on_winning_days}/day`} toneClass="text-bull" />
        <Cell label="Losing Days" value={`${account.losing_days} @ ${account.avg_trades_on_losing_days}/day`} toneClass="text-bear" />
        <Cell label="Expectancy / Trade" value={money(account.trade_expectancy)} toneClass={tone(account.trade_expectancy)} />
        <Cell label="Profit Factor" value={account.profit_factor} toneClass={account.profit_factor >= 1 ? 'text-bull' : 'text-bear'} />
        <Cell label="Worst Peak" value={`${money(account.loss_peak_pnl)} after ${account.loss_peak_after_trades} trades`} toneClass="text-bear" />
        <Cell label="Best Peak" value={`${money(account.win_peak_pnl)} after ${account.win_peak_after_days} days`} toneClass="text-bull" />
        <Cell label="Net Realized" value={money(account.realized_after_charges)} toneClass={tone(account.realized_after_charges)} />
      </div>
    </div>
  );
}
