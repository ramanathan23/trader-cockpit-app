'use client';

import { useMemo } from 'react';
import { filterSignals } from '@/domain/signal';
import { useClock } from '@/hooks/useMarketStatus';
import { useSignals } from '@/hooks/useSignals';
import { useNotes } from '@/hooks/useNotes';
import { useTokenStatus } from '@/hooks/useTokenStatus';
import { Header } from '@/components/Header';
import { ConnectionDot } from '@/components/ui/ConnectionDot';
import { AppRail } from './AppRail';
import { CockpitMain } from './CockpitMain';
import { useCockpitState } from './useCockpitState';
import { OPEN_PHASES } from './appTypes';
import type { InitialConfigs } from './appTypes';

export function CockpitApp({ initialConfigs }: { initialConfigs?: InitialConfigs | null }) {
  const clock       = useClock();
  const tokenStatus = useTokenStatus();
  const { signals, paused, pendingCount, connState, metricsCache, marketStatus, togglePause, clearSignals } = useSignals();
  const { notes, noteEntries, addNote, deleteNote, saveNote } = useNotes();

  const { view, setView, category, setCategory, minAdvCr, setMinAdvCr, viewMode, setViewMode, showHelp, setShowHelp, theme, setTheme, subType, setSubType, fnoOnly, setFnoOnly } = useCockpitState();

  const marketOpen    = OPEN_PHASES.has(marketStatus.phase) && connState === 'connected';
  const filteredCount = useMemo(
    () => filterSignals(signals, category, minAdvCr, metricsCache, subType, fnoOnly).length,
    [signals, category, minAdvCr, metricsCache, subType, fnoOnly],
  );

  return (
    <div className="app-shell h-screen overflow-hidden text-sm text-fg">
      <div className="flex h-full flex-col">
        <Header phase={marketStatus.phase} bias={marketStatus.bias} clock={clock} theme={theme} tokenStatus={tokenStatus}
          onToggleTheme={() => setTheme(m => m === 'dark' ? 'light' : 'dark')}
          viewMode={viewMode} onViewMode={setViewMode} showViewToggle={view === 'live'}
          showHelp={showHelp} onToggleHelp={() => setShowHelp(v => !v)} />
        <div className="flex min-h-0 flex-1">
          <AppRail view={view} onView={setView} signalCount={signals.length} filteredCount={filteredCount} />
          <CockpitMain view={view} setView={setView} signals={signals}
            metricsCache={metricsCache} marketOpen={marketOpen} notes={notes} saveNote={saveNote}
            noteEntries={noteEntries} onAddNote={addNote} onDeleteNote={deleteNote}
            filteredCount={filteredCount} paused={paused} pendingCount={pendingCount}
            togglePause={togglePause} clearSignals={clearSignals}
            category={category} setCategory={setCategory} subType={subType} setSubType={setSubType}
            fnoOnly={fnoOnly} setFnoOnly={setFnoOnly} minAdvCr={minAdvCr} setMinAdvCr={setMinAdvCr}
            viewMode={viewMode} setViewMode={setViewMode} showHelp={showHelp}
            initialConfigs={initialConfigs} />
        </div>
      </div>
      <ConnectionDot state={connState} />
    </div>
  );
}
