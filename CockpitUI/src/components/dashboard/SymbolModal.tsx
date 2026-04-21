'use client';

import { useState } from 'react';
import { X } from 'lucide-react';
import { DailyChart } from './DailyChart';
import { OptionChainPanel } from './OptionChainPanel';

export type SymbolModalTab = 'chart' | 'oc';

interface SymbolModalProps {
  symbol: string;
  initialTab?: SymbolModalTab;
  onClose: () => void;
}

/**
 * Unified symbol detail modal — Chart and Option Chain tabs.
 * 80 % viewport, closes only via X button.
 */
export function SymbolModal({ symbol, initialTab = 'chart', onClose }: SymbolModalProps) {
  const [tab, setTab] = useState<SymbolModalTab>(initialTab);

  return (
    <div
      className="modal-backdrop"
      onKeyDown={event => { if (event.key === 'Escape') onClose(); }}
      tabIndex={-1}
    >
      <div
        className="surface-card flex flex-col overflow-hidden"
        style={{ width: '80vw', height: '80vh' }}
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
