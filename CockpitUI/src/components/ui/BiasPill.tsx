'use client';

import { memo } from 'react';
import type { Bias, IndexName } from '@/domain/market';

export const BiasPill = memo(({ name, value }: { name: IndexName; value: Bias }) => {
  const bullish = value === 'BULLISH';
  const bearish = value === 'BEARISH';
  const color  = bullish ? 'rgb(var(--bull))' : bearish ? 'rgb(var(--bear))' : 'rgb(var(--ghost))';
  const marker = bullish ? 'UP' : bearish ? 'DN' : 'FLAT';

  return (
    <span className="chip gap-1.5" title={`${name.toUpperCase()} bias: ${value}`}>
      <span className="text-[9px] text-ghost">{name.toUpperCase()}</span>
      <span className="num text-[10px]" style={{ color }}>{marker}</span>
    </span>
  );
});
BiasPill.displayName = 'BiasPill';
