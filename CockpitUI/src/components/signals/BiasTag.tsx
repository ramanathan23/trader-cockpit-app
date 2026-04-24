'use client';

import { memo } from 'react';
import { dirColor, type Direction } from '@/domain/signal';

export const BiasTag = memo(({ label, bias }: { label: string; bias: Direction }) => (
  <span
    className="num rounded border border-border bg-base/50 px-1.5 py-0.5 text-[9px] font-black"
    style={{ color: dirColor(bias) }}
  >
    {label} {bias === 'BULLISH' ? 'UP' : 'DN'}
  </span>
));
BiasTag.displayName = 'BiasTag';
