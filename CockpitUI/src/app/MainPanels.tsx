'use client';

import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { Signal } from '@/domain/signal';
import type { NoteEntry } from '@/hooks/useNotes';
import { AccountsPanel } from '@/components/accounts/AccountsPanel';
import { AdminPanel } from '@/components/admin/AdminPanel';
import { OverviewDashboard } from '@/components/overview/OverviewDashboard';
import { StockListPanel } from '@/components/stocklist/StockListPanel';
import type { AppView, InitialConfigs } from './appTypes';

interface MainPanelsProps {
  view: AppView;
  signals: Signal[];
  metricsCache: Record<string, InstrumentMetrics | null>;
  marketOpen: boolean;
  noteEntries: Record<string, NoteEntry[]>;
  onAddNote: (symbol: string, text: string) => void;
  onDeleteNote: (symbol: string, id: string) => void;
  initialConfigs?: InitialConfigs | null;
}

export function MainPanels({
  view, signals, metricsCache, marketOpen, noteEntries, onAddNote, onDeleteNote, initialConfigs,
}: MainPanelsProps) {
  return (
    <>
      <div className={view !== 'overview' ? 'hidden' : 'contents'}>
        <OverviewDashboard active={view === 'overview'} signals={signals}
          metricsCache={metricsCache} marketOpen={marketOpen} noteEntries={noteEntries} />
      </div>
      <div className={view !== 'stocks' ? 'hidden' : 'contents'}>
        <StockListPanel active={view === 'stocks'} noteEntries={noteEntries}
          onAddNote={onAddNote} onDeleteNote={onDeleteNote} />
      </div>
      <div className={view !== 'accounts' ? 'hidden' : 'contents'}>
        <AccountsPanel />
      </div>
      <div className={view !== 'admin' ? 'hidden' : 'contents'}>
        <AdminPanel initialConfigs={initialConfigs} />
      </div>
    </>
  );
}

