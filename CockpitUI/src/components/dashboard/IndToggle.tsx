'use client';

import { memo } from 'react';

/** Toggleable indicator button — colored swatch + label, active/inactive state. */
export const IndToggle = memo(({ label, color, on, onClick }: {
  label: string; color: string; on: boolean; onClick: () => void;
}) => (
  <button type="button" onClick={onClick}
    className={`seg-btn flex items-center gap-1 text-[9px] ${on ? 'active' : ''}`}>
    <span style={{
      display: 'inline-block', width: 8, height: 8, borderRadius: 1, flexShrink: 0,
      background: on ? color : 'transparent',
      border: `1px solid ${color}`,
    }} />
    {label}
  </button>
));
IndToggle.displayName = 'IndToggle';
