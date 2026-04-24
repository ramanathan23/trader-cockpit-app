'use client';

import type { Signal, SignalCategory, SignalType } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { DashboardResponse } from '@/domain/dashboard';
import { HelpLegend } from '@/components/HelpLegend';
import { SignalToolbar } from '@/components/signals/SignalToolbar';
import { SignalFeed } from '@/components/signals/SignalFeed';
import { ScreenerPanel } from '@/components/screener/ScreenerPanel';
import { DashboardPanel } from '@/components/dashboard/DashboardPanel';
import { AdminPanel } from '@/components/admin/AdminPanel';
import { HistoryBar } from './HistoryBar';
import type { AppView, InitialConfigs } from './appTypes';
import type { useHistory } from '@/hooks/useHistory';

type History = ReturnType<typeof useHistory>;

interface CockpitMainProps {
  view:            AppView;
  history:         History;
  currentSignals:  Signal[];
  metricsCache:    Record<string, InstrumentMetrics | null>;
  marketOpen:      boolean;
  notes:           Record<string, string>;
  saveNote:        (id: string, text: string) => void;
  filteredCount:   number;
  paused:          boolean;
  pendingCount:    number;
  togglePause:     () => void;
  clearSignals:    () => void;
  category:        SignalCategory;    setCategory:    (v: SignalCategory) => void;
  subType:         SignalType | null; setSubType:     (v: SignalType | null) => void;
  fnoOnly:         boolean;           setFnoOnly:     (v: boolean) => void;
  minAdvCr:        number;            setMinAdvCr:    (v: number) => void;
  viewMode:        'card' | 'table';  setViewMode:    (v: 'card' | 'table') => void;
  showHelp:        boolean;
  setView:         (v: AppView) => void;
  initialDashboard?: DashboardResponse | null;
  initialConfigs?:   InitialConfigs | null;
}

export function CockpitMain({ view, setView, history, currentSignals, metricsCache, marketOpen, notes, saveNote, filteredCount, paused, pendingCount, togglePause, clearSignals, category, setCategory, subType, setSubType, fnoOnly, setFnoOnly, minAdvCr, setMinAdvCr, viewMode, setViewMode, showHelp, initialDashboard, initialConfigs }: CockpitMainProps) {
  const isSignalView = view === 'live' || view === 'history';

  return (
    <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
      {isSignalView && (
        <SignalToolbar category={category} onCategory={setCategory} subType={subType} onSubType={setSubType}
          fnoOnly={fnoOnly} onFnoOnly={setFnoOnly} minAdvCr={minAdvCr} onMinAdv={setMinAdvCr}
          signals={currentSignals} metricsCache={metricsCache} paused={paused} pendingCount={pendingCount}
          onTogglePause={togglePause} onClear={clearSignals} activeView={view} onViewChange={setView} />
      )}
      {showHelp && <HelpLegend />}
      {view === 'history' && (
        <HistoryBar date={history.date} dates={history.availableDates} loading={history.loading} onDate={history.loadHistory} />
      )}

      {/* Always-mounted panels — no remount on tab switch, state preserved */}
      <div className={view !== 'dashboard' ? 'hidden' : 'contents'}>
        <DashboardPanel active={view === 'dashboard'} initialData={initialDashboard} marketOpen={marketOpen} />
      </div>
      <div className={view !== 'screener' ? 'hidden' : 'contents'}>
        <ScreenerPanel active={view === 'screener'} viewMode={viewMode} onViewMode={setViewMode} marketOpen={marketOpen} />
      </div>
      <div className={view !== 'admin' ? 'hidden' : 'contents'}>
        <AdminPanel initialConfigs={initialConfigs} />
      </div>

      {isSignalView && (
        <SignalFeed signals={currentSignals} metricsCache={metricsCache} marketOpen={marketOpen}
          notes={notes} onSaveNote={saveNote} category={category} subType={subType} fnoOnly={fnoOnly}
          minAdvCr={minAdvCr} viewMode={viewMode}
          emptyLabel={view === 'live' ? 'Waiting for live signals' : `No signals for ${history.date}`}
          hasMore={view === 'history' ? history.hasMore : false}
          onLoadMore={view === 'history' ? history.loadMore : undefined} />
      )}

      <div className="shrink-0 border-t border-border bg-panel/80 px-4 py-2 text-[11px] text-ghost">
        <div className="flex items-center justify-between gap-3">
          <span className="num">{filteredCount}/{currentSignals.length} signals</span>
          <span className="hidden sm:inline">Dashboard data is local to your services and refreshes through the active view.</span>
        </div>
      </div>
    </main>
  );
}
