'use client';

import { memo } from 'react';
import { cn } from '@/lib/cn';
import { signalColor, type SignalCategory, type SignalType } from '@/domain/signal';
import { TABS, SUBTYPES_BY_CATEGORY, VALUE_TIERS, TAB_SIGNAL_TYPE } from './signalToolbarConfig';

interface SignalWorkspaceControlsProps {
  category: SignalCategory;
  onCategory: (c: SignalCategory) => void;
  subType: SignalType | null;
  onSubType: (t: SignalType | null) => void;
  fnoOnly: boolean;
  onFnoOnly: (v: boolean) => void;
  minAdvCr: number;
  onMinAdv: (cr: number) => void;
}

/** Category tabs, subtype filters, F&O toggle, and ADV tier buttons for the live/history workspace. */
export const SignalWorkspaceControls = memo(({ category, onCategory, subType, onSubType, fnoOnly, onFnoOnly, minAdvCr, onMinAdv }: SignalWorkspaceControlsProps) => {
  const activeSubtypes = SUBTYPES_BY_CATEGORY[category];

  const chooseCategory = (next: SignalCategory) => {
    onCategory(next);
    if (!SUBTYPES_BY_CATEGORY[next]) onSubType(null);
  };

  return (
    <>
      <div className="min-w-0 flex-1">
        <div className="seg-group max-w-full">
          {TABS.map(tab => {
            const active = category === tab.key;
            const color  = signalColor(TAB_SIGNAL_TYPE[tab.key]);
            return (
              <button key={tab.key} type="button" title={tab.title}
                onClick={() => chooseCategory(tab.key)}
                className={`seg-btn ${active ? 'active' : ''}`}
                style={active ? { color } : undefined}>
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {activeSubtypes && (
        <div className="seg-group">
          {activeSubtypes.map(item => {
            const active = subType === item.type;
            return (
              <button key={item.type} type="button" title={item.title}
                onClick={() => onSubType(active ? null : item.type)}
                className={`seg-btn ${active ? 'active' : ''}`}
                style={active ? { color: signalColor(item.type) } : undefined}>
                {item.label}
              </button>
            );
          })}
        </div>
      )}

      <button type="button" onClick={() => onFnoOnly(!fnoOnly)}
        className={cn('seg-btn border border-border', fnoOnly && 'active text-violet')}
        title="Show only F&O stocks">F&O</button>

      <div className="seg-group">
        {VALUE_TIERS.map(tier => (
          <button key={tier.cr} type="button" onClick={() => onMinAdv(tier.cr)} title={tier.title}
            className={cn('seg-btn', minAdvCr === tier.cr && 'active text-amber')}>
            {tier.label}
          </button>
        ))}
      </div>
    </>
  );
});
SignalWorkspaceControls.displayName = 'SignalWorkspaceControls';
