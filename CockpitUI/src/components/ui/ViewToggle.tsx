'use client';

import { LayoutGrid, List, Map } from 'lucide-react';
import { cn } from '@/lib/cn';

type ViewMode = 'card' | 'table' | 'heatmap';

interface ViewToggleProps {
  view:     ViewMode;
  onChange: (v: ViewMode) => void;
}

const BTNS: { mode: ViewMode; icon: React.ReactNode; label: string }[] = [
  { mode: 'card',    icon: <LayoutGrid size={14} aria-hidden />, label: 'Card view'    },
  { mode: 'table',   icon: <List       size={14} aria-hidden />, label: 'Table view'   },
  { mode: 'heatmap', icon: <Map        size={14} aria-hidden />, label: 'Heatmap view' },
];

export function ViewToggle({ view, onChange }: ViewToggleProps) {
  return (
    <div className="seg-group">
      {BTNS.map(b => (
        <button key={b.mode} type="button" onClick={() => onChange(b.mode)}
          title={b.label} aria-label={b.label}
          className={cn('seg-btn px-2', view === b.mode && 'active')}>
          {b.icon}
        </button>
      ))}
    </div>
  );
}
