'use client';

import { memo } from 'react';
import { filterSignals, signalColor, type Signal, type SignalCategory, type SignalType } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { ViewToggle } from '@/components/ui/ViewToggle';

// Representative signal type per category — used to pick a highlight color
const TAB_SIGNAL_TYPE: Record<SignalCategory, string> = {
  ALL:     'OPEN_DRIVE_ENTRY',
  DRIVE:   'OPEN_DRIVE_ENTRY',
  SPIKE:   'SPIKE_BREAKOUT',
  ABS:     'ABSORPTION',
  EXHAUST: 'EXHAUSTION_REVERSAL',
  FADE:    'FADE_ALERT',
  BREAK:   'RANGE_BREAKOUT',
  VWAP:    'VWAP_BREAKOUT',
  CAM:     'CAM_H4_BREAKOUT',
};

const CAM_SUBTYPES: { type: SignalType; label: string; title: string }[] = [
  { type: 'CAM_H4_BREAKOUT',  label: 'H4\u2191',  title: 'H4 cross — price crossed above Camarilla H4 resistance (momentum long)' },
  { type: 'CAM_L4_BREAKDOWN', label: 'S4\u2193',  title: 'S4 cross — price crossed below Camarilla L4 support (momentum short)' },
  { type: 'CAM_H3_REVERSAL',  label: 'H3\u2935',  title: 'H3 rejection — wicked into H3 but closed below (fade short)' },
  { type: 'CAM_L3_REVERSAL',  label: 'S3\u2934',  title: 'S3 rejection — wicked into L3 but closed above (fade long)' },
];

const BREAK_SUBTYPES: { type: SignalType; label: string; title: string }[] = [
  { type: 'ORB_BREAKOUT',    label: 'ORB\u2191',  title: 'Opening Range Breakout — closed above opening range high on volume' },
  { type: 'ORB_BREAKDOWN',   label: 'ORB\u2193',  title: 'Opening Range Breakdown — closed below opening range low on volume' },
  { type: 'PDH_BREAKOUT',    label: 'PDH\u2191',  title: 'Previous Day High cross — closed above PDH on volume (momentum long)' },
  { type: 'PDL_BREAKDOWN',   label: 'PDL\u2193',  title: 'Previous Day Low cross — closed below PDL on volume (momentum short)' },
  { type: 'RANGE_BREAKOUT',  label: 'RNG\u2191',  title: '5-candle consolidation broken upward on volume' },
  { type: 'RANGE_BREAKDOWN', label: 'RNG\u2193',  title: '5-candle consolidation broken downward on volume' },
  { type: 'WEEK52_BREAKOUT', label: '52W\u2191',  title: '52-week high breakout on 2× volume — major momentum signal' },
  { type: 'WEEK52_BREAKDOWN',label: '52W\u2193',  title: '52-week low breakdown on 2× volume — major breakdown signal' },
];

const SUBTYPES_BY_CATEGORY: Partial<Record<SignalCategory, { type: SignalType; label: string; title: string }[]>> = {
  CAM:   CAM_SUBTYPES,
  BREAK: BREAK_SUBTYPES,
};

const TABS: { key: SignalCategory; label: string; title: string }[] = [
  { key: 'ALL',     label: 'ALL',      title: 'Show all signal categories' },
  { key: 'DRIVE',   label: 'DRIVE',    title: 'Open drive entries — aggressive momentum when price breaks pre-market range at the open' },
  { key: 'SPIKE',   label: 'SPIKE',    title: 'Volume spike breakouts — unusual volume vs 20-day avg, often signals institutional activity' },
  { key: 'ABS',     label: 'ABS',      title: 'Absorption — large sell orders absorbed at support; potential bullish reversal setup building' },
  { key: 'EXHAUST', label: 'EXHAUST',  title: 'Exhaustion reversals — climactic price move on extreme volume; trend likely to reverse' },
  { key: 'FADE',    label: 'FADE',     title: 'Fade setups — overbought/oversold counter-trend entries when order flow thins out' },
  { key: 'BREAK',   label: 'BREAKOUT', title: 'Breakouts: Opening Range (ORB), Previous Day High/Low, 52-week highs/lows, and range breakouts' },
  { key: 'VWAP',    label: 'VWAP',     title: 'VWAP signals — price reclaiming or breaking below Volume-Weighted Average Price (institutional benchmark)' },
  { key: 'CAM',     label: 'CAM',      title: 'Camarilla pivots — H3/L3 reversals and H4/L4 breakouts based on previous day’s range' },
];

const VALUE_TIERS = [
  { label: 'All',    cr: 0,   title: 'No liquidity filter — show all stocks' },
  { label: '5Cr+',   cr: 5,   title: 'Min ₹5 Cr avg daily traded value — filters very illiquid stocks' },
  { label: '25Cr+',  cr: 25,  title: 'Min ₹25 Cr avg daily value — mid-cap liquidity' },
  { label: '100Cr+', cr: 100, title: 'Min ₹100 Cr avg daily value — large cap, safer for bigger positions' },
  { label: '500Cr+', cr: 500, title: 'Min ₹500 Cr avg daily value — index-grade mega-cap stocks only' },
];

interface SignalToolbarProps {
  // Category filter
  category: SignalCategory;
  onCategory: (c: SignalCategory) => void;
  // Sub-type filter (active for CAM and BREAK categories)
  subType: SignalType | null;
  onSubType: (t: SignalType | null) => void;
  // F&O filter
  fnoOnly: boolean;
  onFnoOnly: (v: boolean) => void;
  // Value filter
  minAdvCr: number;
  onMinAdv: (cr: number) => void;
  // Context counts
  signals: Signal[];
  metricsCache: Record<string, InstrumentMetrics | null>;
  // Controls
  paused: boolean;
  pendingCount: number;
  onTogglePause: () => void;
  onClear: () => void;
  // View toggle
  viewMode: 'card' | 'table';
  onViewMode: (v: 'card' | 'table') => void;
  // Navigation
  activeView: 'dashboard' | 'live' | 'history' | 'screener';
  onViewChange: (v: 'dashboard' | 'live' | 'history' | 'screener') => void;
  // Help legend
  showHelp: boolean;
  onToggleHelp: () => void;
}

export const SignalToolbar = memo(({
  category, onCategory, subType, onSubType,
  fnoOnly, onFnoOnly,
  minAdvCr, onMinAdv,
  signals, metricsCache,
  paused, pendingCount, onTogglePause, onClear,
  viewMode, onViewMode,
  activeView, onViewChange,
  showHelp, onToggleHelp,
}: SignalToolbarProps) => {
  const filtered = filterSignals(signals, category, minAdvCr, metricsCache, subType, fnoOnly);  const activeSubtypes = SUBTYPES_BY_CATEGORY[category];

  return (
    <div className="shrink-0 flex items-center flex-wrap gap-2.5 px-3 py-2 bg-panel border-b border-border z-10 xl:px-4">

      {/* ── View navigation (left-most) ─────────────────────────── */}
      <div className="seg-group">
        {(['dashboard', 'live', 'history', 'screener'] as const).map(v => (
          <button
            key={v}
            onClick={() => onViewChange(v)}
            className={`seg-btn ${activeView === v ? 'active' : ''}`}
            style={activeView === v ? { color: '#2d7ee8' } : undefined}
          >
            {v === 'dashboard' ? 'DASHBOARD' : v === 'live' ? 'LIVE' : v === 'history' ? 'HISTORY' : 'SCREENER'}
          </button>
        ))}
      </div>

      {/* Divider */}
      <div className="w-px h-4 bg-border" />

      {/* ── Category tabs ──────────────────────────────────────── */}
      <div className="seg-group">
        {TABS.map(tab => {
          const active   = category === tab.key;
          const tabColor = signalColor(TAB_SIGNAL_TYPE[tab.key] as Parameters<typeof signalColor>[0]);
          return (
            <button
              key={tab.key}
              onClick={() => onCategory(tab.key)}
              title={tab.title}
              className={`seg-btn ${active ? 'active' : ''}`}
              style={active ? { color: tabColor } : undefined}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* ── Sub-type filter (visible for CAM and BREAK tabs) ── */}
      {activeSubtypes && (
        <>
          <div className="w-px h-4 bg-border" />
          <div className="seg-group">
            {activeSubtypes.map(t => (
              <button
                key={t.type}
                onClick={() => onSubType(subType === t.type ? null : t.type)}
                title={t.title}
                className={`seg-btn ${subType === t.type ? 'active' : ''}`}
                style={subType === t.type ? { color: category === 'CAM' ? '#9b72f7' : '#0dbd7d' } : undefined}
              >
                {t.label}
              </button>
            ))}
          </div>
        </>
      )}

      {/* ── Right cluster ──────────────────────────────────────── */}
      <div className="ml-auto flex items-center gap-2 flex-wrap justify-end">

        {/* ── F&O toggle ──────────────────────────────────────── */}
        <button
          onClick={() => onFnoOnly(!fnoOnly)}
          title="Show only F&O stocks"
          className={`seg-btn ${fnoOnly ? 'active' : ''}`}
          style={fnoOnly ? { color: '#c678dd' } : undefined}
        >
          F&amp;O
        </button>

        {/* ── Value (ADV) tier filter ───────────────────────── */}
        <div className="seg-group">
          {VALUE_TIERS.map(t => (
            <button
              key={t.cr}
              onClick={() => onMinAdv(t.cr)}
              title={t.title}
              className={`seg-btn ${minAdvCr === t.cr ? 'active' : ''}`}
              style={minAdvCr === t.cr ? { color: '#e8933a' } : undefined}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Divider */}
        <div className="w-px h-4 bg-border" />

        {/* Signal count */}
        <span className="num text-[10px] tabular-nums text-ghost hidden md:block" title="Filtered signals / total signals in session">
          {filtered.length}/{signals.length}
        </span>

        {/* Clear */}
        <button
          onClick={onClear}
          title="Clear all signals from the feed"
          className="text-[10px] font-semibold text-ghost hover:text-bear transition-colors px-1"
        >
          CLEAR
        </button>

        {/* Pause / Resume */}
        <button
          onClick={onTogglePause}
          title={paused ? `Resume — ${pendingCount} signal${pendingCount !== 1 ? 's' : ''} queued` : 'Pause incoming signals — they will queue until resumed'}
          className={`text-[10px] font-bold px-2.5 py-1 rounded-[4px] border flex items-center gap-1.5 transition-all ${
            paused
              ? 'border-amber/40 text-amber bg-amber/8'
              : 'border-border text-ghost hover:text-amber hover:border-amber/40'
          }`}
        >
          {paused ? '▶ RESUME' : '⏸ PAUSE'}
          {paused && pendingCount > 0 && (
            <span className="bg-amber text-base text-[9px] font-black px-1.5 rounded-full">{pendingCount}</span>
          )}
        </button>

        {/* Card / table view toggle */}
        {activeView !== 'screener' && (
          <ViewToggle view={viewMode} onChange={onViewMode} />
        )}

        {/* Help toggle */}
        <button
          onClick={onToggleHelp}
          title={showHelp ? 'Hide help legend' : 'Show help legend — explains all metrics, signal types and phases'}
          className={`w-6 h-6 flex items-center justify-center rounded text-[11px] font-black border transition-all ${
            showHelp
              ? 'border-accent/50 text-accent bg-accent/10'
              : 'border-border text-ghost hover:text-fg hover:border-rim'
          }`}
        >
          ?
        </button>
      </div>
    </div>
  );
});

SignalToolbar.displayName = 'SignalToolbar';
