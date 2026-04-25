'use client';

import { memo, useState } from 'react';
import { X, Maximize2, Minimize2 } from 'lucide-react';
import { cn } from '@/lib/cn';
import { DailyChart } from './DailyChart';
import { OptionChainPanel } from './OptionChainPanel';
import { SymbolModalDetails } from './SymbolModalDetails';
import type { StockRow } from '@/domain/stocklist';
import type { NoteEntry } from '@/hooks/useNotes';

export type SymbolModalTab = 'details' | 'chart' | 'oc';

interface SymbolModalProps {
  symbol:       string;
  row?:         StockRow;
  initialTab?:  SymbolModalTab;
  onClose:      () => void;
  noteEntries?: NoteEntry[];
  onAddNote?:   (symbol: string, text: string) => void;
  onDeleteNote?: (symbol: string, id: string)  => void;
}

const TABS: { key: SymbolModalTab; label: string }[] = [
  { key: 'details', label: 'Details' },
  { key: 'chart',   label: 'Chart' },
  { key: 'oc',      label: 'Option Chain' },
];

export const SymbolModal = memo(({
  symbol, row, initialTab = 'chart', onClose,
  noteEntries = [], onAddNote, onDeleteNote,
}: SymbolModalProps) => {
  const [tab,      setTab]      = useState<SymbolModalTab>(initialTab);
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="modal-backdrop"
      tabIndex={-1}
      onKeyDown={e => { if (e.key === 'Escape') onClose(); }}
    >
      <div
        className="surface-card flex flex-col overflow-hidden transition-all duration-200"
        style={expanded ? { width: '100vw', height: '100vh' } : { width: '82vw', height: '82vh' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-4">
            <span className="text-[15px] font-black text-fg">{symbol}</span>
            {row?.company_name && (
              <span className="max-w-[200px] truncate text-[11px] text-ghost">{row.company_name}</span>
            )}
            <div className="seg-group">
              {TABS.map(t => (
                <button key={t.key} type="button"
                  className={cn('seg-btn', tab === t.key && 'active')}
                  onClick={() => setTab(t.key)}>
                  {t.label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button type="button" className="icon-btn h-8 w-8"
              title={expanded ? 'Restore' : 'Expand'}
              onClick={() => setExpanded(e => !e)}>
              {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
            <button type="button" className="icon-btn h-8 w-8" title="Close" onClick={onClose}>
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className={cn('flex-1 overflow-y-auto p-5', tab !== 'details' && 'hidden')}>
            <SymbolModalDetails
              symbol={symbol} row={row}
              entries={noteEntries}
              onAdd={onAddNote} onDelete={onDeleteNote}
            />
          </div>
          <div className={cn('flex-1 overflow-hidden', tab !== 'chart' && 'hidden')}>
            <DailyChart symbol={symbol} height="100%" />
          </div>
          <div className={cn('flex flex-1 flex-col overflow-hidden', tab !== 'oc' && 'hidden')}>
            <OptionChainPanel symbol={symbol} onClose={onClose} embedded />
          </div>
        </div>
      </div>
    </div>
  );
});
SymbolModal.displayName = 'SymbolModal';
