'use client';

import { memo } from 'react';
import { advColor, pctColor, type Signal } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { cn } from '@/lib/cn';
import { fmt2, fmtAdv, spct } from '@/lib/fmt';
import { MetricCell } from './MetricCell';

interface SignalCardMetricsProps {
  signal: Signal;
  metrics: InstrumentMetrics;
}

/** Grid of instrument metrics shown on the signal card (52H/L, ATR, ADV, CHG, open-drive flags). */
export const SignalCardMetrics = memo(({ signal: s, metrics: m }: SignalCardMetricsProps) => (
  <div className="grid grid-cols-3 gap-3 border-t border-border px-3 py-3">
    {m.week52_high && s.price != null && (
      <MetricCell label="52H" title="Distance from 52-week high">
        <span style={{ color: pctColor(s.price, m.week52_high) }}>{spct(s.price, m.week52_high)}</span>
      </MetricCell>
    )}
    {m.week52_low && s.price != null && (
      <MetricCell label="52L" title="Distance from 52-week low">
        <span style={{ color: pctColor(s.price, m.week52_low) }}>{spct(s.price, m.week52_low)}</span>
      </MetricCell>
    )}
    {m.atr_14 != null && (
      <MetricCell label="ATR">
        <span className="text-amber">{fmt2(m.atr_14)}</span>
      </MetricCell>
    )}
    {m.adv_20_cr != null && (
      <MetricCell label="ADV">
        <span style={{ color: advColor(m.adv_20_cr) }}>{fmtAdv(m.adv_20_cr)}</span>
      </MetricCell>
    )}
    {m.day_chg_pct != null && (
      <MetricCell label="CHG%">
        <span className={cn(m.day_chg_pct >= 0 ? 'text-bull' : 'text-bear')}>
          {m.day_chg_pct >= 0 ? '+' : ''}{m.day_chg_pct.toFixed(2)}%
        </span>
      </MetricCell>
    )}
    {m.day_high && m.day_open && Math.abs(m.day_high - m.day_open) / m.day_open < 0.001 && (
      <MetricCell label="Open"><span className="text-bear">O=H</span></MetricCell>
    )}
    {m.day_low && m.day_open && Math.abs(m.day_open - m.day_low) / m.day_open < 0.001 && (
      <MetricCell label="Open"><span className="text-bull">O=L</span></MetricCell>
    )}
  </div>
));
SignalCardMetrics.displayName = 'SignalCardMetrics';
