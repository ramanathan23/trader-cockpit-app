'use client';

import { useCallback, useEffect, useState } from 'react';
import { filterSignals, type SignalCategory } from '@/domain/signal';
import { useClock } from '@/hooks/useMarketStatus';
import { useSignals } from '@/hooks/useSignals';
import { useHistory } from '@/hooks/useHistory';
import { useNotes } from '@/hooks/useNotes';
import { useTokenStatus } from '@/hooks/useTokenStatus';
import { Header } from '@/components/Header';
import { HelpLegend } from '@/components/HelpLegend';
import { SignalToolbar } from '@/components/signals/SignalToolbar';
import { SignalFeed } from '@/components/signals/SignalFeed';
import { ScreenerPanel } from '@/components/screener/ScreenerPanel';
import { DashboardPanel } from '@/components/dashboard/DashboardPanel';
import { ConnectionDot } from '@/components/ui/ConnectionDot';

type AppView = 'dashboard' | 'live' | 'history' | 'screener';
type ThemeMode = 'dark' | 'light';

// ── History date bar ─────────────────────────────────────────────────────────
function HistoryBar({
  date, dates, loading, onDate,
}: {
  date: string;
  dates: string[];
  loading: boolean;
  onDate: (d: string) => void;
}) {
  return (
    <div className="shrink-0 flex items-center gap-3 px-4 py-2 bg-panel border-b border-border flex-wrap">
      <span className="text-[9px] font-bold tracking-[0.14em] uppercase text-ghost">DATE</span>
      <input
        type="date"
        value={date}
        onChange={e => onDate(e.target.value)}
        className="bg-card border border-border text-fg text-xs rounded-[4px] px-2 py-0.5 focus:outline-none"
        style={{ colorScheme: 'inherit' }}
      />
      <div className="seg-group">
        {dates.slice(0, 7).map(d => (
          <button
            key={d}
            onClick={() => onDate(d)}
            className={`seg-btn ${date === d ? 'active' : ''}`}
            style={date === d ? { color: '#2d7ee8' } : undefined}
          >
            {d}
          </button>
        ))}
      </div>
      {loading && <span className="text-[10px] animate-blink text-ghost">Loading…</span>}
    </div>
  );
}

// ── Root app ─────────────────────────────────────────────────────────────────
export function CockpitApp() {
  const clock = useClock();
  const { signals, paused, pendingCount, connState, metricsCache, marketStatus, togglePause, clearSignals } = useSignals();
  const { notes, saveNote } = useNotes();
  const history = useHistory();
  const tokenStatus = useTokenStatus();

  const [view,       setView]       = useState<AppView>('dashboard');
  const [category,   setCategory]   = useState<SignalCategory>('ALL');
  const [subType,    setSubType]    = useState<import('@/domain/signal').SignalType | null>(null);
  const [fnoOnly,    setFnoOnly]    = useState(false);
  const [minAdvCr,   setMinAdvCr]   = useState(0);

  const handleCategory = useCallback((c: SignalCategory) => {
    setCategory(c);
    setSubType(null);
  }, []);
  const [viewMode,   setViewMode]   = useState<'card' | 'table'>('card');
  const [histViewMode, setHistViewMode] = useState<'card' | 'table'>('card');
  const [showHelp,   setShowHelp]   = useState(false);
  const [theme,      setTheme]      = useState<ThemeMode>('dark');

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const stored = window.localStorage.getItem('trader-cockpit-theme');
    if (stored === 'dark' || stored === 'light') {
      setTheme(stored);
      return;
    }

    setTheme(window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem('trader-cockpit-theme', theme);
  }, [theme]);

  // Lazy-load history data when switching to history view
  useEffect(() => {
    if (view === 'history' && history.signals.length === 0 && !history.loading) {
      history.loadHistory(history.date);
    }
  }, [view]); // eslint-disable-line react-hooks/exhaustive-deps

  // Prefetch metrics for history signals (single batch call)
  useEffect(() => {
    if (history.signals.length > 0) {
      const syms = [...new Set(history.signals.map(s => s.symbol))]
        .filter(sym => !(sym in metricsCache));
      if (syms.length === 0) return;
      fetch('/api/v1/instruments/metrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: syms }),
      }).catch(() => {});
    }
  }, [history.signals.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // Blink tab title on background signal
  const blinkTab = (symbol: string) => {
    if (typeof document === 'undefined') return;
    const orig = document.title;
    let n = 0;
    const iv = setInterval(() => {
      document.title = n++ % 2 === 0 ? `⚡ ${symbol}` : orig;
      if (n > 8) { clearInterval(iv); document.title = orig; }
    }, 600);
  };
  void blinkTab; // suppress unused warning — wired in signal push

  const currentSignals   = view === 'history' ? history.signals : signals;
  const currentViewMode  = view === 'history' ? histViewMode : viewMode;
  const onCurrentViewMode = view === 'history' ? setHistViewMode : setViewMode;

  const filteredCount = filterSignals(currentSignals, category, minAdvCr, metricsCache, subType, fnoOnly).length;

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-base text-fg text-sm">
      <Header
        phase={marketStatus.phase}
        bias={marketStatus.bias}
        clock={clock}
        theme={theme}
        onToggleTheme={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
        tokenStatus={tokenStatus}
      />

      <SignalToolbar
        category={category}   onCategory={handleCategory}
        subType={subType}     onSubType={setSubType}
        fnoOnly={fnoOnly}     onFnoOnly={setFnoOnly}
        minAdvCr={minAdvCr}   onMinAdv={setMinAdvCr}
        signals={currentSignals}
        metricsCache={metricsCache}
        paused={paused}
        pendingCount={pendingCount}
        onTogglePause={togglePause}
        onClear={clearSignals}
        viewMode={currentViewMode}
        onViewMode={onCurrentViewMode}
        activeView={view}
        onViewChange={setView}
        showHelp={showHelp}
        onToggleHelp={() => setShowHelp(h => !h)}
      />

      {/* Help legend */}
      {showHelp && <HelpLegend />}

      {/* History date picker */}
      {view === 'history' && (
        <HistoryBar
          date={history.date}
          dates={history.availableDates}
          loading={history.loading}
          onDate={history.loadHistory}
        />
      )}

      {/* Main content area */}
      {view === 'dashboard' ? (
        <DashboardPanel active={view === 'dashboard'} />
      ) : view === 'screener' ? (
        <ScreenerPanel active={view === 'screener'} />
      ) : (
        <SignalFeed
          signals={currentSignals}
          metricsCache={metricsCache}
          notes={notes}
          onSaveNote={saveNote}
          category={category}
          subType={subType}
          fnoOnly={fnoOnly}
          minAdvCr={minAdvCr}
          viewMode={currentViewMode}
          emptyLabel={
            view === 'live'
              ? 'Waiting for signals — market opens at 09:15 IST'
              : `No signals for ${history.date}`
          }
          hasMore={view === 'history' ? history.hasMore : false}
          onLoadMore={view === 'history' ? history.loadMore : undefined}
        />
      )}

      {/* Footer: filtered count + connection indicator */}
      <div className="shrink-0 flex items-center justify-between px-4 py-1 bg-panel border-t border-border text-[10px] text-ghost">
        <span className="num tabular-nums">
          {filteredCount}/{currentSignals.length} signals
        </span>
      </div>

      <ConnectionDot state={connState} />
    </div>
  );
}
