'use client';

import { fmt2 } from '@/lib/fmt';

export interface LivePriceData {
  ltp: number | null;
  prevClose: number | null;
}

interface LivePriceProps {
  ltp?: number | null;
  prevClose?: number | null;
  marketOpen: boolean;
  className?: string;
}

function priceDir(ltp?: number | null, prevClose?: number | null): 'bull' | 'bear' | 'neutral' {
  if (ltp == null || prevClose == null || prevClose === 0) return 'neutral';
  const chg = (ltp - prevClose) / prevClose;
  if (chg > 0.0001) return 'bull';
  if (chg < -0.0001) return 'bear';
  return 'neutral';
}

const DIR_COLOR = {
  bull:    'rgb(var(--bull))',
  bear:    'rgb(var(--bear))',
  neutral: 'rgb(var(--ghost))',
} as const;

const DIR_BG = {
  bull:    'rgba(13,177,118,0.10)',
  bear:    'rgba(229,73,93,0.10)',
  neutral: 'rgba(109,124,132,0.06)',
} as const;

export function LivePrice({ ltp, prevClose, marketOpen, className }: LivePriceProps) {
  const price = ltp ?? prevClose;
  if (price == null) return null;

  const dir = priceDir(ltp, prevClose);
  const live = marketOpen && ltp != null;
  const tip = live
    ? `Live price${prevClose != null ? ` · prev close ${fmt2(prevClose)}` : ''}`
    : `Last price${prevClose != null ? ` · prev close ${fmt2(prevClose)}` : ''}`;

  return (
    <span
      className={`num inline-block rounded px-1 py-0.5 text-[12px] font-black tabular-nums ${live ? 'animate-price-blink' : ''} ${className ?? ''}`}
      style={{
        color:      DIR_COLOR[dir],
        background: live ? DIR_BG[dir] : 'transparent',
        lineHeight: '1.2',
      }}
      title={tip}
    >
      {fmt2(price)}
    </span>
  );
}
