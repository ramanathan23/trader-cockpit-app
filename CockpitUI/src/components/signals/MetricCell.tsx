'use client';

import { memo, type ReactNode } from 'react';

export const MetricCell = memo(({ label, title, children }: { label: string; title?: string; children: ReactNode }) => (
  <div className="min-w-0" title={title}>
    <div className="text-[9px] font-black uppercase text-ghost">{label}</div>
    <div className="num mt-0.5 truncate text-[11px] font-bold">{children}</div>
  </div>
));
MetricCell.displayName = 'MetricCell';
