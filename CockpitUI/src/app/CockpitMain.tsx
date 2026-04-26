'use client';

import type { Signal, SignalCategory, SignalType } from '@/domain/signal';
import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { NoteEntry } from '@/hooks/useNotes';
import { HelpLegend } from '@/components/HelpLegend';
import { SignalToolbar } from '@/components/signals/SignalToolbar';
import { SignalFeed } from '@/components/signals/SignalFeed';
import { LiveHeatMapView } from '@/components/heatmap/LiveHeatMapView';
import { HistoryBar } from './HistoryBar';
import { MainPanels } from './MainPanels';
import type { AppView, InitialConfigs } from './appTypes';
import type { useHistory } from '@/hooks/useHistory';

type History = ReturnType<typeof useHistory>;
type SignalViewMode = 'card' | 'table' | 'heatmap';

interface CockpitMainProps {
  view: AppView; setView: (v: AppView) => void; history: History;
  currentSignals: Signal[]; metricsCache: Record<string, InstrumentMetrics | null>;
  marketOpen: boolean; notes: Record<string, string>; saveNote: (id: string, text: string) => void;
  noteEntries: Record<string, NoteEntry[]>; onAddNote: (symbol: string, text: string) => void;
  onDeleteNote: (symbol: string, id: string) => void; filteredCount: number;
  paused: boolean; pendingCount: number; togglePause: () => void; clearSignals: () => void;
  category: SignalCategory; setCategory: (v: SignalCategory) => void;
  subType: SignalType | null; setSubType: (v: SignalType | null) => void;
  fnoOnly: boolean; setFnoOnly: (v: boolean) => void; minAdvCr: number; setMinAdvCr: (v: number) => void;
  viewMode: SignalViewMode; setViewMode: (v: SignalViewMode) => void; showHelp: boolean;
  initialConfigs?: InitialConfigs | null;
}

export function CockpitMain(props: CockpitMainProps) {
  const { view, history, currentSignals, metricsCache, marketOpen, noteEntries, onAddNote, onDeleteNote, initialConfigs } = props;
  const isSignalView = view === 'live' || view === 'history';
  return (
    <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
      {isSignalView && <Toolbar {...props} />}
      {props.showHelp && <HelpLegend />}
      {view === 'history' && <HistoryBar date={history.date} dates={history.availableDates} loading={history.loading} onDate={history.loadHistory} />}
      <MainPanels view={view} signals={currentSignals} metricsCache={metricsCache}
        marketOpen={marketOpen} noteEntries={noteEntries} onAddNote={onAddNote}
        onDeleteNote={onDeleteNote} initialConfigs={initialConfigs} />
      {isSignalView && <SignalBody {...props} />}
      {isSignalView && <SignalFooter filteredCount={props.filteredCount} total={currentSignals.length} />}
    </main>
  );
}

function Toolbar(p: CockpitMainProps) {
  return (
    <SignalToolbar category={p.category} onCategory={p.setCategory} subType={p.subType} onSubType={p.setSubType}
      fnoOnly={p.fnoOnly} onFnoOnly={p.setFnoOnly} minAdvCr={p.minAdvCr} onMinAdv={p.setMinAdvCr}
      signals={p.currentSignals} metricsCache={p.metricsCache} paused={p.paused} pendingCount={p.pendingCount}
      onTogglePause={p.togglePause} onClear={p.clearSignals} activeView={p.view} onViewChange={p.setView} />
  );
}

function SignalBody(p: CockpitMainProps) {
  if (p.viewMode === 'heatmap') {
    return <LiveHeatMapView metricsCache={p.metricsCache} signals={p.currentSignals}
      category={p.category} subType={p.subType} fnoOnly={p.fnoOnly} minAdvCr={p.minAdvCr} />;
  }
  return <SignalFeed signals={p.currentSignals} metricsCache={p.metricsCache} marketOpen={p.marketOpen}
    notes={p.notes} onSaveNote={p.saveNote} category={p.category} subType={p.subType}
    fnoOnly={p.fnoOnly} minAdvCr={p.minAdvCr} viewMode={p.viewMode}
    emptyLabel={p.view === 'live' ? 'Waiting for live signals' : `No signals for ${p.history.date}`}
    hasMore={p.view === 'history' ? p.history.hasMore : false}
    onLoadMore={p.view === 'history' ? p.history.loadMore : undefined} />;
}

function SignalFooter({ filteredCount, total }: { filteredCount: number; total: number }) {
  return (
    <div className="shrink-0 border-t border-border bg-panel/80 px-4 py-2 text-[11px] text-ghost">
      <div className="flex items-center justify-between gap-3">
        <span className="num">{filteredCount}/{total} signals</span>
        <span className="hidden sm:inline">Data is local to your services.</span>
      </div>
    </div>
  );
}

