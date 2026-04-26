'use client';

import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/cn';
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

type PriceTone = 'bull' | 'bear' | 'neutral';
type TickFlash = 'up' | 'down' | null;

export function priceDir(ltp?: number | null, prevClose?: number | null): PriceTone {
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

export function FlashPrice({
  price,
  prevClose,
  className,
  showBackground = false,
  title,
}: {
  price?: number | null;
  prevClose?: number | null;
  className?: string;
  showBackground?: boolean;
  title?: string;
}) {
  const lastPriceRef = useRef<number | null>(price ?? null);
  const flashSeqRef = useRef(0);
  const [flash, setFlash] = useState<{ dir: TickFlash; seq: number }>({ dir: null, seq: 0 });

  useEffect(() => {
    if (price == null) {
      lastPriceRef.current = null;
      return;
    }

    const previous = lastPriceRef.current;
    lastPriceRef.current = price;
    if (previous == null || previous === price) return;

    const nextSeq = flashSeqRef.current + 1;
    flashSeqRef.current = nextSeq;
    setFlash({ dir: price > previous ? 'up' : 'down', seq: nextSeq });
    const timer = window.setTimeout(() => {
      setFlash(current => (current.seq === nextSeq ? { dir: null, seq: current.seq } : current));
    }, 620);
    return () => window.clearTimeout(timer);
  }, [price]);

  if (price == null) return <span className="text-ghost">-</span>;

  const tone = priceDir(price, prevClose);
  const flashClass = flash.dir === 'up'
    ? 'price-flash price-flash-up'
    : flash.dir === 'down'
      ? 'price-flash price-flash-down'
      : '';

  return (
    <span
      key={flash.seq}
      className={cn(
        'num inline-block rounded px-1 py-0.5 font-black tabular-nums',
        flashClass,
        className,
      )}
      style={{
        color:      DIR_COLOR[tone],
        background: showBackground ? DIR_BG[tone] : undefined,
        lineHeight: '1.2',
      }}
      title={title}
    >
      {fmt2(price)}
    </span>
  );
}

export function LivePrice({ ltp, prevClose, marketOpen, className }: LivePriceProps) {
  const price = ltp ?? prevClose;
  if (price == null) return null;

  const live = marketOpen && ltp != null;
  const tip = live
    ? `Live price${prevClose != null ? ` · prev close ${fmt2(prevClose)}` : ''}`
    : `Last price${prevClose != null ? ` · prev close ${fmt2(prevClose)}` : ''}`;

  return (
    <FlashPrice
      price={price}
      prevClose={prevClose}
      className={cn('text-[12px]', className)}
      showBackground={live}
      title={tip}
    />
  );
}
