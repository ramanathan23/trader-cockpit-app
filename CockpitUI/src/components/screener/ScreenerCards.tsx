'use client';

import { memo, useRef, useMemo } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { ScreenerRow } from '@/domain/screener';
import { advColor } from '@/domain/signal';
import { fmt2, fmtAdv } from '@/lib/fmt';

interface ScreenerCardsProps {
  rows:    ScreenerRow[];
  loading: boolean;
}

const ProximityBar = memo(({ pct, inverted = false }: { pct?: number | null; inverted?: boolean }) => {
  if (pct == null) return null;
  const raw   = inverted ? Math.min(0, pct) : pct;
  const width = Math.min(100, Math.abs(raw));
  const color = inverted
    ? (raw >= -2 ? '#0dbd7d' : raw >= -10 ? '#e8933a' : '#f23d55')
    : (raw > 50  ? '#0dbd7d' : raw > 20   ? '#e8933a' : '#f23d55');

  return (
    <div className="w-full rounded-full h-[3px] overflow-hidden" style={{ background: '#172035' }}>
      <div className="h-[3px] rounded-full transition-all" style={{ width: `${width}%`, background: color }} />
    </div>
  );
});
ProximityBar.displayName = 'ProximityBar';

const ScreenerCard = memo(({ row: r }: { row: ScreenerRow }) => {
  const f52hColor = r.f52h == null ? '#2a3f58' : r.f52h >= -2 ? '#0dbd7d' : r.f52h >= -10 ? '#e8933a' : '#f23d55';
  const f52lColor = r.f52l == null ? '#2a3f58' : r.f52l > 50  ? '#0dbd7d' : r.f52l > 20   ? '#e8933a' : '#f23d55';
  const dvwapColor = r.dvwap_delta_pct == null ? '#2a3f58' : r.dvwap_delta_pct >= 0 ? '#0dbd7d' : '#f23d55';
  const ema50Color = r.ema50_delta_pct == null ? '#2a3f58' : r.ema50_delta_pct >= 0 ? '#0dbd7d' : '#f23d55';
  const ema200Color = r.ema200_delta_pct == null ? '#2a3f58' : r.ema200_delta_pct >= 0 ? '#0dbd7d' : '#f23d55';

  return (
    <div className="w-44 rounded-md border border-border bg-card hover:bg-lift transition-colors p-3 flex flex-col gap-2.5">
      {/* Symbol + ADV */}
      <div className="flex items-start justify-between">
        <span className="font-bold text-[13px] tracking-wide text-fg">{r.symbol}</span>
        {r.adv_20_cr != null && (
          <span
            className="num text-[9px] font-bold px-1.5 py-0.5 rounded-sm"
            style={{ color: advColor(r.adv_20_cr), background: `${advColor(r.adv_20_cr)}15` }}
          >
            {fmtAdv(r.adv_20_cr)}
          </span>
        )}
      </div>

      {/* Close price + ATR */}
      <div className="flex items-baseline gap-2">
        <span className="num font-bold text-[15px] text-fg tabular-nums">{fmt2(r.display_price)}</span>
        {r.atr_14 != null && (
          <span className="text-[9px]" style={{ color: '#2a3f58' }}>
            ATR <span className="num" style={{ color: '#e8933a' }}>{r.atr_14.toFixed(2)}</span>
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-1 text-[9px]">
        <span className="rounded-sm px-1.5 py-1 text-center font-bold" style={{ color: dvwapColor, background: `${dvwapColor}15` }}>
          DV {r.dvwap_delta_pct != null ? `${r.dvwap_delta_pct >= 0 ? '+' : ''}${r.dvwap_delta_pct.toFixed(1)}%` : '—'}
        </span>
        <span className="rounded-sm px-1.5 py-1 text-center font-bold" style={{ color: ema50Color, background: `${ema50Color}15` }}>
          50E {r.ema50_delta_pct != null ? `${r.ema50_delta_pct >= 0 ? '+' : ''}${r.ema50_delta_pct.toFixed(1)}%` : '—'}
        </span>
        <span className="rounded-sm px-1.5 py-1 text-center font-bold" style={{ color: ema200Color, background: `${ema200Color}15` }}>
          200E {r.ema200_delta_pct != null ? `${r.ema200_delta_pct >= 0 ? '+' : ''}${r.ema200_delta_pct.toFixed(1)}%` : '—'}
        </span>
      </div>

      {/* 52H proximity */}
      <div>
        <div className="flex justify-between text-[9px] mb-1">
          <span style={{ color: '#1e2e4a' }}>52H%</span>
          <span className="num font-bold" style={{ color: f52hColor }}>
            {r.f52h != null ? (r.f52h >= 0 ? '+' : '') + r.f52h.toFixed(1) + '%' : '—'}
          </span>
        </div>
        <ProximityBar pct={r.f52h} inverted />
      </div>

      {/* 52L proximity */}
      <div>
        <div className="flex justify-between text-[9px] mb-1">
          <span style={{ color: '#1e2e4a' }}>52L%</span>
          <span className="num font-bold" style={{ color: f52lColor }}>
            {r.f52l != null ? '+' + r.f52l.toFixed(1) + '%' : '—'}
          </span>
        </div>
        <ProximityBar pct={r.f52l} />
      </div>

      <div className="grid grid-cols-3 gap-1 text-[9px]" style={{ color: '#1e2e4a' }}>
        <span>WK <span className="num" style={{ color: '#5a7796' }}>{r.week_return_pct != null ? `${r.week_return_pct >= 0 ? '+' : ''}${r.week_return_pct.toFixed(1)}%` : '—'}</span></span>
        <span>W+ <span className="num" style={{ color: '#5a7796' }}>{r.week_gain_pct != null ? `+${r.week_gain_pct.toFixed(1)}%` : '—'}</span></span>
        <span>W- <span className="num" style={{ color: '#5a7796' }}>{r.week_decline_pct != null ? `${r.week_decline_pct.toFixed(1)}%` : '—'}</span></span>
      </div>
    </div>
  );
});
ScreenerCard.displayName = 'ScreenerCard';

export const ScreenerCards = memo(({ rows, loading }: ScreenerCardsProps) => {
  const parentRef = useRef<HTMLDivElement>(null);

  // Approximate cards per row: container ~full width, card ~176px + 12px gap
  const COLS_PER_ROW = 8;
  const ROW_HEIGHT = 220;

  const chunkedRows = useMemo(() => {
    const chunks: ScreenerRow[][] = [];
    for (let i = 0; i < rows.length; i += COLS_PER_ROW) {
      chunks.push(rows.slice(i, i + COLS_PER_ROW));
    }
    return chunks;
  }, [rows]);

  const rowVirtualizer = useVirtualizer({
    count: chunkedRows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 3,
  });

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-xs animate-blink" style={{ color: '#2a3f58' }}>
        Loading metrics…
      </div>
    );
  }
  if (rows.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-xs gap-2" style={{ color: '#2a3f58' }}>
        <span className="text-2xl opacity-20">⊞</span>
        <span>No data — adjust filters</span>
      </div>
    );
  }

  const virtualItems = rowVirtualizer.getVirtualItems();
  const totalSize = rowVirtualizer.getTotalSize();

  return (
    <div ref={parentRef} className="flex-1 overflow-y-auto p-4">
      <div style={{ height: totalSize, position: 'relative' }}>
        {virtualItems.map(vi => (
          <div
            key={vi.index}
            style={{
              position: 'absolute',
              top: vi.start,
              left: 0,
              right: 0,
            }}
            className="flex flex-wrap gap-3"
          >
            {chunkedRows[vi.index].map(r => <ScreenerCard key={r.symbol} row={r} />)}
          </div>
        ))}
      </div>
    </div>
  );
});
ScreenerCards.displayName = 'ScreenerCards';
