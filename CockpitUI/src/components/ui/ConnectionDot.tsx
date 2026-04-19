'use client';

import type { ConnState } from '@/hooks/useSignals';

export function ConnectionDot({ state }: { state: ConnState }) {
  const color =
    state === 'connected' ? 'rgb(var(--bull))' :
    state === 'disconnected' ? 'rgb(var(--bear))' :
    'rgb(var(--amber))';

  const label =
    state === 'connected' ? 'Live' :
    state === 'disconnected' ? 'Reconnecting' :
    'Connecting';

  return (
    <div className="fixed bottom-4 right-4 z-40 flex items-center gap-2 rounded-full border border-border bg-card/95 px-3 py-1.5 text-[11px] shadow-card backdrop-blur">
      <span
        className={`inline-block h-1.5 w-1.5 rounded-full ${state !== 'connected' ? 'animate-blink' : ''}`}
        style={{
          backgroundColor: color,
          boxShadow: state === 'connected' ? `0 0 10px ${color}` : 'none',
        }}
      />
      <span className="num font-bold" style={{ color }}>{label}</span>
    </div>
  );
}
