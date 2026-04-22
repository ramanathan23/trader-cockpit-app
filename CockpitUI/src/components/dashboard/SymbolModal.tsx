'use client';

import { useState } from 'react';
import { X, Maximize2, Minimize2 } from 'lucide-react';
import { DailyChart } from './DailyChart';
import { OptionChainPanel } from './OptionChainPanel';

export type SymbolModalTab = 'chart' | 'oc';

interface SymbolModalProps {
  symbol: string;
  initialTab?: SymbolModalTab;
  onClose: () => void;
}

export function SymbolModal({ symbol, initialTab = 'chart', onClose }: SymbolModalProps) {
  const [tab,      setTab]      = useState<SymbolModalTab>(initialTab);
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="modal-backdrop"
      onKeyDown={event => { if (event.key === 'Escape') onClose(); }}
      tabIndex={-1}
    >
      <div
        className="surface-card flex flex-col overflow-hidden transition-all duration-200"
        style={expanded ? { width: '100vw', height: '100vh' } : { width: '80vw', height: '80vh' }}
        onClick={event => event.stopPropagation()}
      >
        {/* ── header ── */}
        <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-4">
            <span className="text-[15px] font-black text-fg">{symbol}</span>
            <div className="seg-group">
              <button
                type="button"
                onClick={() => setTab('chart')}
                className={`seg-btn ${tab === 'chart' ? 'active' : ''}`}
              >
                Chart
              </button>
              <button
                type="button"
                onClick={() => setTab('oc')}
                className={`seg-btn ${tab === 'oc' ? 'active' : ''}`}
              >
                Option Chain
              </button>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setExpanded(e => !e)}
              className="icon-btn h-8 w-8"
              title={expanded ? 'Restore size' : 'Expand to full screen'}
              aria-label={expanded ? 'Restore' : 'Expand'}
            >
              {expanded ? <Minimize2 size={14} aria-hidden="true" /> : <Maximize2 size={14} aria-hidden="true" />}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="icon-btn h-8 w-8"
              title="Close"
              aria-label="Close"
            >
              <X size={15} aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* ── content ── */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className={`flex-1 overflow-hidden ${tab === 'chart' ? '' : 'hidden'}`}>
            <DailyChart symbol={symbol} height="100%" />
          </div>
          <div className={`flex flex-1 flex-col overflow-hidden ${tab === 'oc' ? '' : 'hidden'}`}>
            <OptionChainPanel symbol={symbol} onClose={onClose} embedded />
          </div>
        </div>
      </div>
    </div>
  );
}
