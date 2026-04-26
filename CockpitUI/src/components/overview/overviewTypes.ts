import type { InstrumentMetrics } from '@/domain/instrument_metrics';
import type { Signal } from '@/domain/signal';
import type { StockRow } from '@/domain/stocklist';
import type { NoteEntry } from '@/hooks/useNotes';
import type { LivePriceData } from '@/components/ui/LivePrice';

export interface OverviewDashboardProps {
  active: boolean;
  signals: Signal[];
  metricsCache: Record<string, InstrumentMetrics | null>;
  marketOpen: boolean;
  noteEntries: Record<string, NoteEntry[]>;
}

export interface SymbolClickProps {
  onSymbol: (symbol: string) => void;
}

export interface RowsProps {
  rows: StockRow[];
}

export interface SignalProps {
  signals: Signal[];
}

export interface LiveRowsProps extends RowsProps {
  livePrices: Record<string, LivePriceData>;
}

