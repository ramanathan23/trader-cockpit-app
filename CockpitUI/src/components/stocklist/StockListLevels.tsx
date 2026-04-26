'use client';

import { memo } from 'react';
import type { ReactNode } from 'react';
import { fmt2 } from '@/lib/fmt';
import { screenerPctColor, screenerPctText } from '@/lib/screenerDisplay';
import type { StockRow } from '@/domain/stocklist';

function LvlCell({ label, value, refPrice }: { label: string; value?: number | null; refPrice?: number | null }) {
  const pct = value != null && refPrice ? (value - refPrice) / refPrice * 100 : null;
  return (
    <div className="rounded-md border border-border/30 bg-base/35 px-3 py-2">
      <span className="label-xs block">{label}</span>
      <span className="num mt-1 block text-[14px] font-black leading-none text-fg">{value != null ? fmt2(value) : '-'}</span>
      {pct != null && (
        <span className="num mt-1 block text-[11px] font-bold" style={{ color: screenerPctColor(pct) }}>
          {screenerPctText(pct, true)}
        </span>
      )}
    </div>
  );
}

function LevelGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <div className="label-xs mb-1.5">{title}</div>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">{children}</div>
    </div>
  );
}

interface LevelsProps { row: StockRow; }

export const StockListLevels = memo(({ row }: LevelsProps) => {
  const price = row.display_price ?? row.prev_day_close;
  return (
    <div className="rounded-lg border border-border/50 bg-card/70 p-3">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <div className="label-sm">Key Levels</div>
          <div className="mt-1 text-[11px] text-ghost">Distance shown from current price</div>
        </div>
        {row.rs_vs_nifty != null && (
          <div className="rounded-md border border-border/40 bg-base/45 px-3 py-2 text-right">
            <span className="label-xs block">RS/NIFTY</span>
            <span className="num mt-1 block text-[14px] font-black leading-none" style={{ color: screenerPctColor(row.rs_vs_nifty) }}>
              {screenerPctText(row.rs_vs_nifty, true)}
            </span>
          </div>
        )}
      </div>

      <div className="grid gap-3 2xl:grid-cols-3">
        <LevelGroup title="Range">
          <LvlCell label="52W High" value={row.week52_high} refPrice={price} />
          <LvlCell label="52W Low" value={row.week52_low} refPrice={price} />
          <LvlCell label="Mth High" value={row.prev_month_high} refPrice={price} />
          <LvlCell label="Mth Low" value={row.prev_month_low} refPrice={price} />
        </LevelGroup>
        <LevelGroup title="Session">
          <LvlCell label="PDH" value={row.prev_day_high} refPrice={price} />
          <LvlCell label="PDL" value={row.prev_day_low} refPrice={price} />
          <LvlCell label="Wk High" value={row.prev_week_high} refPrice={price} />
          <LvlCell label="Wk Low" value={row.prev_week_low} refPrice={price} />
        </LevelGroup>
        <LevelGroup title="Trend">
          <LvlCell label="EMA 50" value={row.ema_50} refPrice={price} />
          <LvlCell label="EMA 200" value={row.ema_200} refPrice={price} />
          <LvlCell label="DVWAP" value={row.daily_vwap} refPrice={price} />
        </LevelGroup>
      </div>
    </div>
  );
});
StockListLevels.displayName = 'StockListLevels';
