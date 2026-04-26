'use client';

import type { ReactNode } from 'react';
import { Maximize2, PanelTop, X } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Panel } from './OverviewShell';
import type { ChartKey } from './overviewChartDefs';

interface OverviewChartPanelProps {
  id: ChartKey;
  title: string;
  caption: string;
  className?: string;
  docked: boolean;
  onDock: (id: ChartKey | null) => void;
  onExpand: (id: ChartKey) => void;
  children: ReactNode;
}

export function OverviewChartPanel({
  id, title, caption, className, docked, onDock, onExpand, children,
}: OverviewChartPanelProps) {
  return (
    <Panel title={title} caption={caption} className={className} actions={
      <div className="flex shrink-0 items-center gap-1">
        <button type="button" className={cn('icon-btn h-7 w-7', docked && 'border-accent text-accent')}
          title={docked ? 'Undock' : 'Dock'} onClick={() => onDock(docked ? null : id)}>
          {docked ? <X size={12} /> : <PanelTop size={12} />}
        </button>
        <button type="button" className="icon-btn h-7 w-7" title="Expand" onClick={() => onExpand(id)}>
          <Maximize2 size={12} />
        </button>
      </div>
    }>
      {children}
    </Panel>
  );
}

export function ExpandedChart({
  title, onClose, children,
}: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="modal-backdrop">
      <div className="flex h-[92vh] w-[94vw] flex-col overflow-hidden rounded-lg border border-border bg-panel shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="text-[13px] font-black text-fg">{title}</div>
          <button type="button" className="icon-btn h-8 w-8" title="Close" onClick={onClose}>
            <X size={14} />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-auto p-3">{children}</div>
      </div>
    </div>
  );
}
