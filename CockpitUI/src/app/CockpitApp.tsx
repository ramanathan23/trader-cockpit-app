'use client';

import { useEffect, useMemo, useState } from 'react';
import { filterSignals, type SignalCategory, type SignalType } from '@/domain/signal';
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

const VIEWS: { key: AppView; label: string; caption: string }[] = [
  { key: 'dashboard', label: 'Dashboard', caption: 'Scored universe' },
  { key: 'live', label: 'Live', caption: 'Signal tape' },
  { key: 'history', label: 'History', caption: 'Replay session' },
  { key: 'screener', label: 'Screener', caption: 'Opportunity scan' },
];

function HistoryBar({
  date,
  dates,
  loading,
  onDate,
}: {
  date: string;
  dates: string[];
  loading: boolean;
  onDate: (d: string) => void;
}) {
  return (
    <div className="shrink-0 border-b border-border bg-panel/80 px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-[10px] font-black uppercase text-ghost">Replay date</span>
        <input
          type="date"
          value={date}
          onChange={event => onDate(event.target.value)}
          className="field h-8 text-[12px]"
          style={{ colorScheme: 'inherit' }}
        />
        {dates.length > 0 && (
          <div className="seg-group">
            {dates.slice(0, 7).map(d => (
              <button
                key={d}
                type="button"
                onClick={() => onDate(d)}
                className={`seg-btn ${date === d ? 'active' : ''}`}
                style={date === d ? { color: 'rgb(var(--accent))' } : undefined}
              >
                {d.slice(5)}
              </button>
            ))}
          </div>
        )}
        {loading && <span className="num text-[11px] text-amber">Loading</span>}
      </div>
    </div>
  );
}

function AppRail({
  view,
  onView,
  signalCount,
  filteredCount,
}: {
  view: AppView;
  onView: (view: AppView) => void;
  signalCount: number;
  filteredCount: number;
}) {
  return (
    <aside className="hidden w-[210px] shrink-0 border-r border-border bg-panel/72 p-3 md:block">
      <nav className="flex flex-col gap-1">
        {VIEWS.map(item => {
          const active = item.key === view;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => onView(item.key)}
              className={`rounded-lg border px-3 py-3 text-left transition-colors ${
                active
                  ? 'border-accent/40 bg-accent/10 text-fg'
                  : 'border-transparent text-dim hover:border-border hover:bg-lift/60 hover:text-fg'
              }`}
            >
              <span className="block text-[12px] font-black">{item.label}</span>
              <span className="mt-0.5 block text-[10px] text-ghost">{item.caption}</span>
            </button>
          );
        })}
      </nav>

      <div className="mt-4 rounded-lg border border-border bg-base/50 p-3">
        <div className="text-[10px] font-black uppercase text-ghost">Tape</div>
        <div className="mt-2 flex items-end justify-between">
          <span className="num text-[22px] font-black text-fg">{filteredCount}</span>
          <span className="num text-[11px] text-ghost">of {signalCount}</span>
        </div>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-border">
          <div
            className="h-full rounded-full bg-accent"
            style={{ width: `${signalCount ? Math.min(100, filteredCount / signalCount * 100) : 0}%` }}
          />
        </div>
      </div>
    </aside>
  );
}

export function CockpitApp() {
  const clock = useClock();
  const tokenStatus = useTokenStatus();
  const { signals, paused, pendingCount, connState, metricsCache, marketStatus, togglePause, clearSignals } = useSignals();
  const { notes, saveNote } = useNotes();
  const history = useHistory();

  const [view, setView] = useState<AppView>('dashboard');
  const [category, setCategory] = useState<SignalCategory>('ALL');
  const [minAdvCr, setMinAdvCr] = useState(0);
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card');
  const [histViewMode, setHistViewMode] = useState<'card' | 'table'>('table');
  const [screenerViewMode, setScreenerViewMode] = useState<'card' | 'table'>('table');
  const [showHelp, setShowHelp] = useState(false);
  const [theme, setTheme] = useState<ThemeMode>('dark');
  const [subType, setSubType] = useState<SignalType | null>(null);
  const [fnoOnly, setFnoOnly] = useState(false);

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

  useEffect(() => {
    if (view === 'history' && history.signals.length === 0 && !history.loading) {
      history.loadHistory(history.date);
    }
  }, [view]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (history.signals.length === 0) return;
    const syms = [...new Set(history.signals.map(signal => signal.symbol))]
      .filter(symbol => !(symbol in metricsCache));
    if (syms.length === 0) return;
    fetch('/api/v1/instruments/metrics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbols: syms }),
    }).catch(() => {});
  }, [history.signals.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const currentSignals = view === 'history' ? history.signals : signals;
  const currentViewMode = view === 'history' ? histViewMode : view === 'screener' ? screenerViewMode : viewMode;
  const onCurrentViewMode = view === 'history' ? setHistViewMode : view === 'screener' ? setScreenerViewMode : setViewMode;

  const filteredCount = useMemo(
    () => filterSignals(currentSignals, category, minAdvCr, metricsCache, subType, fnoOnly).length,
    [currentSignals, category, minAdvCr, metricsCache, subType, fnoOnly],
  );

  return (
    <div className="app-shell h-screen overflow-hidden text-sm text-fg">
      <div className="flex h-full flex-col">
        <Header
          phase={marketStatus.phase}
          bias={marketStatus.bias}
          clock={clock}
          theme={theme}
          tokenStatus={tokenStatus}
          onToggleTheme={() => setTheme(mode => mode === 'dark' ? 'light' : 'dark')}
        />

        <div className="flex min-h-0 flex-1">
          <AppRail
            view={view}
            onView={setView}
            signalCount={currentSignals.length}
            filteredCount={filteredCount}
          />

          <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
            <SignalToolbar
              category={category}
              onCategory={setCategory}
              subType={subType}
              onSubType={setSubType}
              fnoOnly={fnoOnly}
              onFnoOnly={setFnoOnly}
              minAdvCr={minAdvCr}
              onMinAdv={setMinAdvCr}
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
              onToggleHelp={() => setShowHelp(value => !value)}
            />

            {showHelp && <HelpLegend />}

            {view === 'history' && (
              <HistoryBar
                date={history.date}
                dates={history.availableDates}
                loading={history.loading}
                onDate={history.loadHistory}
              />
            )}

            {view === 'dashboard' ? (
              <DashboardPanel active={view === 'dashboard'} />
            ) : view === 'screener' ? (
              <ScreenerPanel active={view === 'screener'} viewMode={screenerViewMode} onViewMode={setScreenerViewMode} />
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
                emptyLabel={view === 'live' ? 'Waiting for live signals' : `No signals for ${history.date}`}
                hasMore={view === 'history' ? history.hasMore : false}
                onLoadMore={view === 'history' ? history.loadMore : undefined}
              />
            )}

            <div className="shrink-0 border-t border-border bg-panel/80 px-4 py-2 text-[11px] text-ghost">
              <div className="flex items-center justify-between gap-3">
                <span className="num">{filteredCount}/{currentSignals.length} signals</span>
                <span className="hidden sm:inline">Dashboard data is local to your services and refreshes through the active view.</span>
              </div>
            </div>
          </main>
        </div>
      </div>

      <ConnectionDot state={connState} />
    </div>
  );
}
