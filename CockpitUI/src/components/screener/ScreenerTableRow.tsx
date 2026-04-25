'use client';

import { memo } from 'react';
import type { ScreenerRow } from '@/domain/screener';
import { advColor } from '@/domain/signal';
import { LivePrice } from '@/components/ui/LivePrice';
import { fmtAdv } from '@/lib/fmt';
import { screenerPctColor, screenerPctText, screenerF52hColor, screenerF52lColor, screenerStageColor, screenerStageLabel } from '@/lib/screenerDisplay';

export const ScreenerTableRow = memo(({ row: r, onChart, marketOpen }: {
  row: ScreenerRow;
  onChart?: (sym: string) => void;
  onOptionChain?: (sym: string) => void;
  marketOpen: boolean;
}) => (
  <tr className="cursor-pointer" onClick={() => onChart?.(r.symbol)}>
    <td className="text-left">
      <span className="inline-flex items-center gap-1">
        <span className="text-ticker text-fg">{r.symbol}</span>
        {r.is_fno       && <span className="chip px-1 py-0 text-[9px] text-violet border-violet/35">F&O</span>}
        {r.vcp_detected  && <span className="chip px-1 py-0 text-[9px] text-bull border-bull/35">VCP</span>}
        {r.rect_breakout && <span className="chip px-1 py-0 text-[9px] text-accent border-accent/35">RECT</span>}
      </span>
    </td>
    <td className="text-right"><span className="num text-[11px] font-black" style={{ color: screenerStageColor(r.stage) }}>{screenerStageLabel(r.stage)}</span></td>
    <td className="text-right"><span className="num font-bold" style={{ color: r.adv_20_cr != null ? advColor(r.adv_20_cr) : undefined }}>{fmtAdv(r.adv_20_cr)}</span></td>
    <td className="text-right"><span className="num font-bold text-amber">{r.atr_14 != null ? r.atr_14.toFixed(2) : '-'}</span></td>
    <td className="text-right"><LivePrice ltp={r.current_price} prevClose={r.prev_day_close} marketOpen={marketOpen} className="text-[13px]" /></td>
    <td className="text-right"><span className="num font-bold" style={{ color: screenerPctColor(r.dvwap_delta_pct) }}>{screenerPctText(r.dvwap_delta_pct, true)}</span></td>
    <td className="text-right"><span className="num font-bold" style={{ color: screenerPctColor(r.ema50_delta_pct) }}>{screenerPctText(r.ema50_delta_pct, true)}</span></td>
    <td className="text-right"><span className="num font-bold" style={{ color: screenerPctColor(r.ema200_delta_pct) }}>{screenerPctText(r.ema200_delta_pct, true)}</span></td>
    <td className="text-right"><span className="num font-bold" style={{ color: screenerPctColor(r.rs_vs_nifty) }}>{r.rs_vs_nifty != null ? `${r.rs_vs_nifty > 0 ? '+' : ''}${r.rs_vs_nifty.toFixed(1)}` : '-'}</span></td>
    <td className="text-right"><span className="num font-bold" style={{ color: screenerF52hColor(r.f52h) }}>{screenerPctText(r.f52h)}</span></td>
    <td className="text-right"><span className="num font-bold" style={{ color: screenerF52lColor(r.f52l) }}>{r.f52l != null ? `+${r.f52l.toFixed(1)}%` : '-'}</span></td>
    <td className="text-right"><span className="num font-bold" style={{ color: screenerPctColor(r.week_return_pct) }}>{screenerPctText(r.week_return_pct, true)}</span></td>
    <td className="text-right"><span className="num font-bold" style={{ color: screenerPctColor(r.week_gain_pct, true) }}>{screenerPctText(r.week_gain_pct, true)}</span></td>
    <td className="text-right"><span className="num font-bold" style={{ color: screenerPctColor(r.week_decline_pct, true) }}>{screenerPctText(r.week_decline_pct)}</span></td>
  </tr>
));
ScreenerTableRow.displayName = 'ScreenerTableRow';
