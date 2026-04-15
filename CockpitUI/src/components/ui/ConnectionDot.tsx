'use client';

import type { ConnState } from '@/hooks/useSignals';

export function ConnectionDot({ state }: { state: ConnState }) {
  const color =
    state === 'connected'    ? '#0dbd7d' :
    state === 'disconnected' ? '#f23d55' : '#e8933a';
  const label =
    state === 'connected'    ? 'Live' :
    state === 'disconnected' ? 'Reconnecting' : 'Connecting';

  return (
    <div className="fixed bottom-4 right-4 flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-full bg-card border border-border">
      <span
        className={state !== 'connected' ? 'animate-blink' : ''}
        style={{
          display:         'inline-block',
          width:           '5px',
          height:          '5px',
          borderRadius:    '50%',
          backgroundColor: color,
          boxShadow:       state === 'connected' ? `0 0 6px ${color}80` : 'none',
        }}
      />
      <span className="num" style={{ color }}>{label}</span>
    </div>
  );
}
