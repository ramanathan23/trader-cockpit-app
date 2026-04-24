'use client';

import { memo } from 'react';
import { cn } from '@/lib/cn';
import { SCREENER_PRESETS, type ScreenerPreset } from '@/domain/screener';

interface ScreenerPresetGroupsProps {
  presets: Set<ScreenerPreset>;
  onPreset: (p: ScreenerPreset) => void;
}

function PresetBtn({ preset, active, activeClass, label, onPreset }: {
  preset: ScreenerPreset;
  active: boolean;
  activeClass: string;
  label?: string;
  onPreset: (p: ScreenerPreset) => void;
}) {
  return (
    <button type="button" onClick={() => onPreset(preset)}
      className={cn('seg-btn', active && `active ${activeClass}`)}>
      {label}
    </button>
  );
}

/** All preset filter button groups — ungrouped, CAM, stage, pattern, watchlist. */
export const ScreenerPresetGroups = memo(({ presets, onPreset }: ScreenerPresetGroupsProps) => {
  const byGroup = (group?: string) => SCREENER_PRESETS.filter(p => p.group === group);

  return (
    <>
      <div className="seg-group">
        {byGroup(undefined).map(p => (
          <PresetBtn key={p.key} preset={p.key} active={presets.has(p.key)} activeClass="text-accent" label={p.label} onPreset={onPreset} />
        ))}
      </div>

      <div className="seg-group">
        {byGroup('cam').map(p => (
          <PresetBtn key={p.key} preset={p.key} active={presets.has(p.key)} activeClass="text-violet" label={p.label} onPreset={onPreset} />
        ))}
      </div>

      <div className="seg-group">
        {byGroup('stage').map(p => (
          <PresetBtn key={p.key} preset={p.key} active={presets.has(p.key)} activeClass="text-bull" label={p.label} onPreset={onPreset} />
        ))}
      </div>

      <div className="seg-group">
        {byGroup('pattern').map(p => (
          <PresetBtn key={p.key} preset={p.key} active={presets.has(p.key)} activeClass="text-accent" label={p.label} onPreset={onPreset} />
        ))}
      </div>

      {byGroup('watchlist').map(p => (
        <button key={p.key} type="button" onClick={() => onPreset(p.key)}
          className={cn('seg-btn border border-border', presets.has(p.key) && 'active text-amber')}>
          ★ {p.label}
        </button>
      ))}
    </>
  );
});
ScreenerPresetGroups.displayName = 'ScreenerPresetGroups';
