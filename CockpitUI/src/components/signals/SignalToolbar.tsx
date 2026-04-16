'use client';

import { memo } from 'react';
import { filterSignals, signalColor, type Signal, type SignalCategory } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import { ViewToggle } from '@/components/ui/ViewToggle';

// Representative signal type per category — used to pick a highlight color
const TAB_SIGNAL_TYPE: Record<SignalCategory, string> = {
  ALL:     'OPEN_DRIVE',
  DRIVE:   'OPEN_DRIVE',
  SPIKE:   'VOLUME_SPIKE',
  ABS:     'ABS_STRENGTH',
  EXHAUST: 'EXHAUSTION_REVERSAL',
  FADE:    'FADE_SETUP',
  BREAK:   'RANGE_BREAKOUT',
  VWAP:    'VWAP_RECLAIM',
  CAM:     'CAMARILLA_R3_BREAK',
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
  category, onCategory, minAdvCr, onMinAdv,
  signals, metricsCache,
  paused, pendingCount, onTogglePause, onClear,
  viewMode, onViewMode,
  activeView, onViewChange,
  showHelp, onToggleHelp,
}: SignalToolbarProps) => {
  const filtered = filterSignals(signals, category, minAdvCr, metricsCache);

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

      {/* ── Right cluster ──────────────────────────────────────── */}
      <div className="ml-auto flex items-center gap-2 flex-wrap justify-end">

        {/* Value (ADV) tier filter */}
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
