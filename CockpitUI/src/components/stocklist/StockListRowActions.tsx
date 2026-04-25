'use client';

import { memo } from 'react';
import { BarChart2, Link2, StickyNote } from 'lucide-react';
import { cn } from '@/lib/cn';
import type { SymbolModalTab } from '@/components/dashboard/SymbolModal';

interface StockListRowActionsProps {
  noteCount:   number;
  onOpenModal: (tab: SymbolModalTab) => void;
}

export const StockListRowActions = memo(({ noteCount, onOpenModal }: StockListRowActionsProps) => (
  <div className="flex items-center justify-end gap-0.5">
    <button
      type="button"
      className="icon-btn h-6 w-6"
      title="Open Chart"
      onClick={e => { e.stopPropagation(); onOpenModal('chart'); }}
    >
      <BarChart2 size={11} />
    </button>
    <button
      type="button"
      className="icon-btn h-6 w-6"
      title="Option Chain"
      onClick={e => { e.stopPropagation(); onOpenModal('oc'); }}
    >
      <Link2 size={11} />
    </button>
    <button
      type="button"
      className={cn('icon-btn relative h-6 w-6', noteCount > 0 && 'text-amber')}
      title={`Notes${noteCount > 0 ? ` (${noteCount})` : ''}`}
      onClick={e => { e.stopPropagation(); onOpenModal('details'); }}
    >
      <StickyNote size={11} />
      {noteCount > 0 && (
        <span className="absolute -right-0.5 -top-0.5 flex h-3 w-3 items-center justify-center rounded-full bg-amber num text-[8px] font-black text-base">
          {noteCount > 9 ? '9+' : noteCount}
        </span>
      )}
    </button>
  </div>
));
StockListRowActions.displayName = 'StockListRowActions';
