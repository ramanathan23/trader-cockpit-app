'use client';

import { memo } from 'react';
import { fmt2 } from '@/lib/fmt';

export const LevelRow = memo(({ entry, stop, target }: {
  entry?: number | null;
  stop?: number | null;
  target?: number | null;
}) => {
  if (entry == null && stop == null && target == null) return null;
  return (
    <div className="grid grid-cols-3 gap-2 border-t border-border px-3 py-2 text-[10px] text-ghost">
      <span>E <b className="num text-amber">{fmt2(entry)}</b></span>
      <span>SL <b className="num text-bear">{fmt2(stop)}</b></span>
      <span>T1 <b className="num text-bull">{fmt2(target)}</b></span>
    </div>
  );
});
LevelRow.displayName = 'LevelRow';
