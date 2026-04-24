'use client';

import { memo } from 'react';
import { signalColor, signalDesc, signalShort, type SignalType } from '@/domain/signal';

/** Colored pill badge showing signal type abbreviation — shared by card and table row. */
export const SignalTypeBadge = memo(({ signalType, showDesc }: { signalType: SignalType; showDesc?: boolean }) => {
  const color = signalColor(signalType);
  return (
    <span
      className="rounded-md border px-2 py-1 text-signal-badge uppercase"
      style={{ color, background: `${color}18`, borderColor: `${color}40` }}
      title={showDesc ? signalDesc(signalType) : undefined}
    >
      {signalShort(signalType)}
    </span>
  );
});
SignalTypeBadge.displayName = 'SignalTypeBadge';
