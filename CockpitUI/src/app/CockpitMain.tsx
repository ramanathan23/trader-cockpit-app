'use client';

import type { Signal, SignalCategory, SignalType } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { NoteEntry } from '@/hooks/useNotes';
import { HelpLegend } from '@/components/HelpLegend';
import { SignalToolbar } from '@/components/signals/SignalToolbar';
import { SignalFeed } from '@/components/signals/SignalFeed';
import { StockListPanel } from '@/components/stocklist/StockListPanel';
import { AdminPanel } from '@/components/admin/AdminPanel';
import { AccountsPanel } from '@/components/accounts/AccountsPanel';
import { LiveHeatMapView } from '@/components/heatmap/LiveHeatMapView';
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
  noteEntries:     Record<string, NoteEntry[]>;
  onAddNote:       (symbol: string, text: string) => void;
  onDeleteNote:    (symbol: string, id: string)   => void;
  filteredCount:   number;
  paused:          boolean;
  pendingCount:    number;
  togglePause:     () => void;
  clearSignals:    () => void;
  category:        SignalCategory;    setCategory:    (v: SignalCategory) => void;
  subType:         SignalType | null; setSubType:     (v: SignalType | null) => void;
  fnoOnly:         boolean;           setFnoOnly:     (v: boolean) => void;
  minAdvCr:        number;            setMinAdvCr:    (v: number) => void;
  viewMode:        'card' | 'table' | 'heatmap';  setViewMode:    (v: 'card' | 'table' | 'heatmap') => void;
  showHelp:        boolean;
  setView:         (v: AppView) => void;
  initialConfigs?:   InitialConfigs | null;
}

export function CockpitMain({
  view, setView, history, currentSignals, metricsCache, marketOpen,
  notes, saveNote, noteEntries, onAddNote, onDeleteNote,
  filteredCount, paused, pendingCount, togglePause, clearSignals,
  category, setCategory, subType, setSubType, fnoOnly, setFnoOnly,
  minAdvCr, setMinAdvCr, viewMode, setViewMode, showHelp,
  initialConfigs,
}: CockpitMainProps) {
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

      {/* Always-mounted panels — preserve state across tab switches */}
      <div className={view !== 'stocks' ? 'hidden' : 'contents'}>
        <StockListPanel
          active={view === 'stocks'}
          noteEntries={noteEntries}
          onAddNote={onAddNote}
          onDeleteNote={onDeleteNote}
        />
      </div>
      <div className={view !== 'accounts' ? 'hidden' : 'contents'}>
        <AccountsPanel />
      </div>
      <div className={view !== 'admin' ? 'hidden' : 'contents'}>
        <AdminPanel initialConfigs={initialConfigs} />
      </div>

      {isSignalView && viewMode === 'heatmap' && (
        <LiveHeatMapView
          metricsCache={metricsCache}
          signals={currentSignals}
          category={category}
          subType={subType}
          fnoOnly={fnoOnly}
          minAdvCr={minAdvCr}
        />
      )}
      {isSignalView && viewMode !== 'heatmap' && (
        <SignalFeed signals={currentSignals} metricsCache={metricsCache} marketOpen={marketOpen}
          notes={notes} onSaveNote={saveNote} category={category} subType={subType} fnoOnly={fnoOnly}
          minAdvCr={minAdvCr} viewMode={viewMode}
          emptyLabel={view === 'live' ? 'Waiting for live signals' : `No signals for ${history.date}`}
          hasMore={view === 'history' ? history.hasMore : false}
          onLoadMore={view === 'history' ? history.loadMore : undefined} />
      )}

      {isSignalView && (
        <div className="shrink-0 border-t border-border bg-panel/80 px-4 py-2 text-[11px] text-ghost">
          <div className="flex items-center justify-between gap-3">
            <span className="num">{filteredCount}/{currentSignals.length} signals</span>
            <span className="hidden sm:inline">Data is local to your services.</span>
          </div>
        </div>
      )}
    </main>
  );
}
