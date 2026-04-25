'use client';

import { memo } from 'react';
import { fmt2 } from '@/lib/fmt';
import { screenerPctColor, screenerPctText } from '@/lib/screenerDisplay';
import type { StockRow } from '@/domain/stocklist';

function LvlCell({ label, value, ref: refPrice }: { label: string; value?: number | null; ref?: number | null }) {
  const pct = value != null && refPrice ? (value - refPrice) / refPrice * 100 : null;
  return (
    <div className="flex min-w-[88px] flex-col">
      <span className="label-xs">{label}</span>
      <span className="num text-[14px] font-black text-fg">{value != null ? fmt2(value) : '—'}</span>
      {pct != null && (
        <span className="num text-[11px] font-bold" style={{ color: screenerPctColor(pct) }}>
          {screenerPctText(pct, true)}
        </span>
      )}
    </div>
  );
}

interface LevelsProps { row: StockRow; }

export const StockListLevels = memo(({ row }: LevelsProps) => {
  const price = row.display_price ?? row.prev_day_close;
  return (
    <div className="rounded-lg border border-border/50 bg-card/60 p-3">
      <div className="label-sm mb-2.5">Key Levels</div>
      <div className="flex flex-wrap gap-x-5 gap-y-3">
        <LvlCell label="52W HIGH"  value={row.week52_high}    ref={price} />
        <LvlCell label="52W LOW"   value={row.week52_low}     ref={price} />
        <LvlCell label="PDH"       value={row.prev_day_high}  ref={price} />
        <LvlCell label="PDL"       value={row.prev_day_low}   ref={price} />
        <LvlCell label="EMA 50"    value={row.ema_50}         ref={price} />
        <LvlCell label="EMA 200"   value={row.ema_200}        ref={price} />
        <LvlCell label="WK HIGH"   value={row.prev_week_high} ref={price} />
        <LvlCell label="WK LOW"    value={row.prev_week_low}  ref={price} />
        {row.daily_vwap    && <LvlCell label="DVWAP"    value={row.daily_vwap}    ref={price} />}
        {row.prev_month_high && <LvlCell label="MTH HIGH" value={row.prev_month_high} ref={price} />}
        {row.prev_month_low  && <LvlCell label="MTH LOW"  value={row.prev_month_low}  ref={price} />}
        {row.rs_vs_nifty != null && (
          <div className="flex min-w-[88px] flex-col">
            <span className="label-xs">RS/NIFTY</span>
            <span className="num text-[14px] font-black" style={{ color: screenerPctColor(row.rs_vs_nifty) }}>
              {screenerPctText(row.rs_vs_nifty, true)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
});
StockListLevels.displayName = 'StockListLevels';
