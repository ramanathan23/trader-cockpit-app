'use client';

import { useEffect, useMemo } from 'react';
import { filterSignals } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { DashboardResponse } from '@/domain/dashboard';
import { useClock } from '@/hooks/useMarketStatus';
import { useSignals } from '@/hooks/useSignals';
import { useHistory } from '@/hooks/useHistory';
import { useNotes } from '@/hooks/useNotes';
import { useTokenStatus } from '@/hooks/useTokenStatus';
import { Header } from '@/components/Header';
import { ConnectionDot } from '@/components/ui/ConnectionDot';
import { AppRail } from './AppRail';
import { CockpitMain } from './CockpitMain';
import { useCockpitState } from './useCockpitState';
import { OPEN_PHASES } from './appTypes';
import type { InitialConfigs } from './appTypes';

export function CockpitApp({ initialDashboard, initialConfigs }: { initialDashboard?: DashboardResponse | null; initialConfigs?: InitialConfigs | null }) {
  const clock       = useClock();
  const tokenStatus = useTokenStatus();
  const { signals, paused, pendingCount, connState, metricsCache, marketStatus, mergeMetrics, togglePause, clearSignals } = useSignals();
  const { notes, saveNote } = useNotes();
  const history = useHistory();

  const { view, setView, category, setCategory, minAdvCr, setMinAdvCr, viewMode, setViewMode, showHelp, setShowHelp, theme, setTheme, subType, setSubType, fnoOnly, setFnoOnly } = useCockpitState();

  useEffect(() => {
    if (view === 'history' && history.signals.length === 0 && !history.loading) {
      history.loadHistory(history.date);
    }
  }, [view]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (history.signals.length === 0) return;
    const syms = [...new Set(history.signals.map(s => s.symbol))].filter(sym => !(sym in metricsCache));
    if (syms.length === 0) return;
    fetch('/api/v1/instruments/metrics', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbols: syms }) })
      .then(r => r.ok ? r.json() : null)
      .then((data: Record<string, InstrumentMetrics> | null) => mergeMetrics(data))
      .catch(() => {});
  }, [history.signals, metricsCache, mergeMetrics]);

  const marketOpen     = OPEN_PHASES.has(marketStatus.phase) && connState === 'connected';
  const currentSignals = view === 'history' ? history.signals : signals;
  const filteredCount  = useMemo(
    () => filterSignals(currentSignals, category, minAdvCr, metricsCache, subType, fnoOnly).length,
    [currentSignals, category, minAdvCr, metricsCache, subType, fnoOnly],
  );

  return (
    <div className="app-shell h-screen overflow-hidden text-sm text-fg">
      <div className="flex h-full flex-col">
        <Header phase={marketStatus.phase} bias={marketStatus.bias} clock={clock} theme={theme} tokenStatus={tokenStatus}
          onToggleTheme={() => setTheme(m => m === 'dark' ? 'light' : 'dark')}
          viewMode={viewMode} onViewMode={setViewMode} showViewToggle={view !== 'admin'}
          showHelp={showHelp} onToggleHelp={() => setShowHelp(v => !v)} />
        <div className="flex min-h-0 flex-1">
          <AppRail view={view} onView={setView} signalCount={currentSignals.length} filteredCount={filteredCount} />
          <CockpitMain view={view} setView={setView} history={history} currentSignals={currentSignals}
            metricsCache={metricsCache} marketOpen={marketOpen} notes={notes} saveNote={saveNote}
            filteredCount={filteredCount} paused={paused} pendingCount={pendingCount}
            togglePause={togglePause} clearSignals={clearSignals}
            category={category} setCategory={setCategory} subType={subType} setSubType={setSubType}
            fnoOnly={fnoOnly} setFnoOnly={setFnoOnly} minAdvCr={minAdvCr} setMinAdvCr={setMinAdvCr}
            viewMode={viewMode} setViewMode={setViewMode} showHelp={showHelp}
            initialDashboard={initialDashboard} initialConfigs={initialConfigs} />
        </div>
      </div>
      <ConnectionDot state={connState} />
    </div>
  );
}
