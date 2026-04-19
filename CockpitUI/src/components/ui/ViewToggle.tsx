'use client';

import { Crosshair, LayoutGrid, List } from 'lucide-react';

interface ViewToggleProps {
  view: 'card' | 'table' | 'cluster';
  onChange: (v: 'card' | 'table' | 'cluster') => void;
}

export function ViewToggle({ view, onChange }: ViewToggleProps) {
  return (
    <div className="seg-group">
      <button
        type="button"
        onClick={() => onChange('cluster')}
        title="Cluster chart"
        aria-label="Cluster chart"
        className={`seg-btn px-2 ${view === 'cluster' ? 'active' : ''}`}
      >
        <Crosshair size={14} aria-hidden="true" />
      </button>
      <button
        type="button"
        onClick={() => onChange('card')}
        title="Card view"
        aria-label="Card view"
        className={`seg-btn px-2 ${view === 'card' ? 'active' : ''}`}
      >
        <LayoutGrid size={14} aria-hidden="true" />
      </button>
      <button
        type="button"
        onClick={() => onChange('table')}
        title="Table view"
        aria-label="Table view"
        className={`seg-btn px-2 ${view === 'table' ? 'active' : ''}`}
      >
        <List size={14} aria-hidden="true" />
      </button>
    </div>
  );
}
