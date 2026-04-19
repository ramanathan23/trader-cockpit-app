'use client';

import { memo } from 'react';
import { filterSignals, signalColor, type Signal, type SignalCategory, type SignalType } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';

const TAB_SIGNAL_TYPE: Record<SignalCategory, SignalType> = {
  ALL: 'OPEN_DRIVE_ENTRY',
  DRIVE: 'OPEN_DRIVE_ENTRY',
  SPIKE: 'SPIKE_BREAKOUT',
  ABS: 'ABSORPTION',
  EXHAUST: 'EXHAUSTION_REVERSAL',
  FADE: 'FADE_ALERT',
  BREAK: 'RANGE_BREAKOUT',
  VWAP: 'VWAP_BREAKOUT',
  CAM: 'CAM_H4_BREAKOUT',
};

const TABS: { key: SignalCategory; label: string; title: string }[] = [
  { key: 'ALL', label: 'All', title: 'All signal categories' },
  { key: 'DRIVE', label: 'Drive', title: 'Open drive entries and failures' },
  { key: 'SPIKE', label: 'Spike', title: 'Volume spike breakouts' },
  { key: 'ABS', label: 'Abs', title: 'Absorption setups' },
  { key: 'EXHAUST', label: 'Exhaust', title: 'Exhaustion reversals' },
  { key: 'FADE', label: 'Fade', title: 'Counter-trend fade alerts' },
  { key: 'BREAK', label: 'Breakout', title: 'ORB, PDH/PDL, range and 52-week breakouts' },
  { key: 'VWAP', label: 'VWAP', title: 'VWAP reclaim and breakdown signals' },
  { key: 'CAM', label: 'CAM', title: 'Camarilla pivot breakouts and reversals' },
];

const SUBTYPES_BY_CATEGORY: Partial<Record<SignalCategory, { type: SignalType; label: string; title: string }[]>> = {
  CAM: [
    { type: 'CAM_H4_BREAKOUT', label: 'H4+', title: 'Camarilla H4 breakout' },
    { type: 'CAM_L4_BREAKDOWN', label: 'L4-', title: 'Camarilla L4 breakdown' },
    { type: 'CAM_H3_REVERSAL', label: 'H3 rev', title: 'Camarilla H3 rejection' },
    { type: 'CAM_L3_REVERSAL', label: 'L3 rev', title: 'Camarilla L3 rejection' },
  ],
  BREAK: [
    { type: 'ORB_BREAKOUT', label: 'ORB+', title: 'Opening range breakout' },
    { type: 'ORB_BREAKDOWN', label: 'ORB-', title: 'Opening range breakdown' },
    { type: 'PDH_BREAKOUT', label: 'PDH+', title: 'Previous day high breakout' },
    { type: 'PDL_BREAKDOWN', label: 'PDL-', title: 'Previous day low breakdown' },
    { type: 'RANGE_BREAKOUT', label: 'RNG+', title: 'Range breakout' },
    { type: 'RANGE_BREAKDOWN', label: 'RNG-', title: 'Range breakdown' },
    { type: 'WEEK52_BREAKOUT', label: '52W+', title: '52-week high breakout' },
    { type: 'WEEK52_BREAKDOWN', label: '52W-', title: '52-week low breakdown' },
  ],
};

const VALUE_TIERS = [
  { label: 'All', cr: 0, title: 'No liquidity filter' },
  { label: '5Cr+', cr: 5, title: 'Minimum Rs 5 Cr average daily traded value' },
  { label: '25Cr+', cr: 25, title: 'Minimum Rs 25 Cr average daily traded value' },
  { label: '100Cr+', cr: 100, title: 'Minimum Rs 100 Cr average daily traded value' },
  { label: '500Cr+', cr: 500, title: 'Minimum Rs 500 Cr average daily traded value' },
];

interface SignalToolbarProps {
  category: SignalCategory;
  onCategory: (c: SignalCategory) => void;
  subType: SignalType | null;
  onSubType: (t: SignalType | null) => void;
  fnoOnly: boolean;
  onFnoOnly: (v: boolean) => void;
  minAdvCr: number;
  onMinAdv: (cr: number) => void;
  signals: Signal[];
  metricsCache: Record<string, InstrumentMetrics | null>;
  paused: boolean;
  pendingCount: number;
  onTogglePause: () => void;
  onClear: () => void;
  viewMode?: never;
  onViewMode?: never;
  activeView: 'dashboard' | 'live' | 'history' | 'screener' | 'admin';
  onViewChange: (v: 'dashboard' | 'live' | 'history' | 'screener' | 'admin') => void;
}

export const SignalToolbar = memo(({
  category,
  onCategory,
  subType,
  onSubType,
  fnoOnly,
  onFnoOnly,
  minAdvCr,
  onMinAdv,
  signals,
  metricsCache,
  paused,
  pendingCount,
  onTogglePause,
  onClear,
  activeView,
  onViewChange,
}: SignalToolbarProps) => {
  const signalWorkspace = activeView === 'live' || activeView === 'history';
  const activeSubtypes = SUBTYPES_BY_CATEGORY[category];
  const filtered = filterSignals(signals, category, minAdvCr, metricsCache, subType, fnoOnly);

  const chooseCategory = (next: SignalCategory) => {
    onCategory(next);
    if (!SUBTYPES_BY_CATEGORY[next]) onSubType(null);
  };

  return (
    <div className="shrink-0 border-b border-border bg-panel/88 px-3 py-3 xl:px-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="seg-group md:hidden">
          {(['dashboard', 'live', 'history', 'screener', 'admin'] as const).map(view => (
            <button
              key={view}
              type="button"
              onClick={() => onViewChange(view)}
              className={`seg-btn ${activeView === view ? 'active' : ''}`}
              style={activeView === view ? { color: 'rgb(var(--accent))' } : undefined}
            >
              {view}
            </button>
          ))}
        </div>

        {signalWorkspace && (
          <>
            <div className="min-w-0 flex-1">
              <div className="seg-group max-w-full">
                {TABS.map(tab => {
                  const active = category === tab.key;
                  const color = signalColor(TAB_SIGNAL_TYPE[tab.key]);
                  return (
                    <button
                      key={tab.key}
                      type="button"
                      title={tab.title}
                      onClick={() => chooseCategory(tab.key)}
                      className={`seg-btn ${active ? 'active' : ''}`}
                      style={active ? { color } : undefined}
                    >
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
                    <button
                      key={item.type}
                      type="button"
                      title={item.title}
                      onClick={() => onSubType(active ? null : item.type)}
                      className={`seg-btn ${active ? 'active' : ''}`}
                      style={active ? { color: signalColor(item.type) } : undefined}
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>
            )}

            <button
              type="button"
              onClick={() => onFnoOnly(!fnoOnly)}
              className={`seg-btn border border-border ${fnoOnly ? 'active' : ''}`}
              style={fnoOnly ? { color: 'rgb(var(--violet))' } : undefined}
              title="Show only F&O stocks"
            >
              F&O
            </button>

            <div className="seg-group">
              {VALUE_TIERS.map(tier => (
                <button
                  key={tier.cr}
                  type="button"
                  onClick={() => onMinAdv(tier.cr)}
                  title={tier.title}
                  className={`seg-btn ${minAdvCr === tier.cr ? 'active' : ''}`}
                  style={minAdvCr === tier.cr ? { color: 'rgb(var(--amber))' } : undefined}
                >
                  {tier.label}
                </button>
              ))}
            </div>
          </>
        )}

        <div className="ml-auto flex items-center gap-2">
          {signalWorkspace && (
            <>
              <span className="chip num hidden lg:inline-flex" title="Filtered signals / total signals">
                {filtered.length}/{signals.length}
              </span>
              <button
                type="button"
                onClick={onClear}
                className="icon-btn"
                title="Clear signal tape"
                aria-label="Clear signal tape"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M6 7h12m-10 0 1 13h6l1-13M10 7V4h4v3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>

              <button
                type="button"
                onClick={onTogglePause}
                className={`h-8 rounded-lg border px-3 text-[11px] font-black transition-colors ${
                  paused
                    ? 'border-amber/50 bg-amber/10 text-amber'
                    : 'border-border bg-base/50 text-dim hover:border-rim hover:text-fg'
                }`}
                title={paused ? `${pendingCount} signals queued` : 'Pause incoming signals'}
              >
                {paused ? `Resume${pendingCount > 0 ? ` ${pendingCount}` : ''}` : 'Pause'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
});

SignalToolbar.displayName = 'SignalToolbar';
